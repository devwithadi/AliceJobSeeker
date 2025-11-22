"""
Install the Google AI Python SDK

$ pip install google-generativeai

See the getting started guide for more information:
https://ai.google.dev/gemini-api/docs/get-started/python
"""

import os
import json
import sys
import time

import google.generativeai as genai
from utils import is_empty_string

# Global variables - will be initialized lazily
config = None
model = None
preference_model = None
chat_session = None
_api_configured = False

def load_configuration(config_file="customization.json"):
    """Load configuration from JSON file"""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return {}

def _ensure_api_configured():
    """Ensure the API is configured before use (lazy initialization)"""
    global config, model, preference_model, _api_configured
    
    if _api_configured:
        return True
    
    try:
        # Load configuration
        config = load_configuration()
        
        # Get API key from environment variables with fallback to config file
        api_key = os.environ.get("GEMINI_API_KEY")
        if is_empty_string(api_key):
            api_key = config.get("gemini_api_key")
            if is_empty_string(api_key):
                print("WARNING: No Gemini API key found in environment variables or config file.")
                print("Please set the GEMINI_API_KEY environment variable or add gemini_api_key to customization.json")
                return False
        
        # Configure the API
        genai.configure(api_key=api_key)
        
        # Get model settings from config or use defaults
        generation_config = config.get("gemini_settings", {}).get("generation_config", {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 1000,
            "response_mime_type": "text/plain",
        })
        
        # Create the model for regular questions
        model = genai.GenerativeModel(
            model_name=config.get("gemini_settings", {}).get("model_name", "gemini-1.5-flash"),
            generation_config=generation_config,
            system_instruction=config.get("gemini_settings", {}).get("system_instruction", 
                "remember all this when asked question you will answer from this data.\n"
                "be concise only answer in max 5 words, average of 2 words, min of 1 word\n, "
                "if it is a multi option question only give the index number of the answer")
        )
        
        # Create a separate model for preference matching with different system instruction
        preference_model = genai.GenerativeModel(
            model_name=config.get("gemini_settings", {}).get("preference_model_name", "gemini-1.5-flash"),
            generation_config=config.get("gemini_settings", {}).get("preference_generation_config", {
                "temperature": 0.2,
                "top_p": 0.95,
                "top_k": 64,
                "max_output_tokens": 100,
                "response_mime_type": "text/plain",
            }),
            system_instruction=config.get("gemini_settings", {}).get("preference_system_instruction",
                "You are a job preference matching assistant. "
                "When comparing job descriptions with user preferences, "
                "only respond with 'yes' or 'no' followed by a brief one-sentence explanation. "
                "Be analytical and decisive in your assessment.")
        )
        
        _api_configured = True
        return True
        
    except Exception as e:
        print(f"Error configuring Gemini API: {e}")
        return False

def initialize_chat_session():
    """Initialize the chat session with resume data"""
    global chat_session, model, config
    
    # Ensure API is configured
    if not _ensure_api_configured():
        print("ERROR: Cannot initialize chat session - API not configured")
        return None
    
    # Only initialize if not already initialized
    if chat_session is not None:
        return chat_session
    
    try:
        # Import here to avoid circular dependency
        from resume_parser import get_resume_data
        
        # Get resume data by parsing PDF if configured
        resume_data = get_resume_data(config)
        
        # Convert resume data to string if it's a dictionary
        if isinstance(resume_data, dict):
            resume_data_str = json.dumps(resume_data, indent=2)
        else:
            resume_data_str = str(resume_data)
        
        # Start chat session with context
        chat_session = model.start_chat(
            history=[
                {
                    "role": "user",
                    "parts": [resume_data_str],
                },
                {
                    "role": "model",
                    "parts": ["I've processed your resume information and will use it to answer questions concisely."],
                },
                {
                    "role": "user",
                    "parts": ["remember all this when asked question you will answer from this data.\nyou will answer using this data min 1 word, average 3 words , and max 5 words and any information is not given then you can guess the answer, if nothing is given then you can say guess the answer never leave the question unanswered"],
                },
                {
                    "role": "model",
                    "parts": ["Understood. I will use the provided data for concise answers (1-5 words)."],
                },
            ]
        )
        
        return chat_session
    except Exception as e:
        print(f"Error initializing chat session: {e}")
        # Return None to indicate failure
        return None

def bard_flash_response(question) -> str:
    """Get a response from Gemini API with proper error handling"""
    global chat_session, preference_model, model
    
    # Ensure API is configured
    if not _ensure_api_configured():
        print("ERROR: Cannot get response - API not configured")
        return "Yes"  # Return safe default
    
    # Check for empty input using utility function
    if is_empty_string(question):
        print("Warning: Empty question provided to bard_flash_response")
        return "Yes"  # Return a safe default
    
    # Maximum retry attempts
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Determine if this is a preference matching question
            if "Based on the above information, does this job match my preferences?" in question:
                # Use preference model for job matching questions
                response = preference_model.generate_content(question)
                return response.text
            else:
                # Initialize chat session if needed
                if chat_session is None:
                    chat_session = initialize_chat_session()
                    
                    # If initialization failed, use direct generate_content instead
                    if chat_session is None:
                        print("Warning: Using direct content generation as fallback")
                        response = model.generate_content(question)
                        return response.text
                
                # Use regular chat session for other queries
                response = chat_session.send_message(question)
                return response.text
                
        except Exception as e:
            print(f"An error occurred in bard_flash_response: {e}")
            retry_count += 1
            
            if retry_count < max_retries:
                print(f"Retrying ({retry_count}/{max_retries})...")
                
                # If there was an error with the chat session, try to reinitialize it
                if "chat_session" in str(e).lower() or "history" in str(e).lower():
                    print("Attempting to reinitialize chat session")
                    chat_session = None
                    
                time.sleep(1)  # Short pause before retry
            else:
                # Return a generic safe response that won't cause subsequent errors
                if "multiple_choice" in str(e).lower() or "options" in str(e).lower():
                    return "1"  # Default to first option for multiple choice
                return "Yes"  # Default generic response
    
    # If we exhausted all retries
    return "Yes"  # Default generic response

