import os
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Gemini model fallback chain — tries each until one works
FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]

def _get_api_keys():
    """Return list of all available Gemini API keys (primary + backups)."""
    keys = []
    primary = os.getenv("GOOGLE_API_KEY", "")
    if primary:
        keys.append(primary)
    backup = os.getenv("GOOGLE_API_KEY_BACKUP", "")
    if backup:
        keys.append(backup)
    return keys if keys else [None]

# Set the scopes for Google API
SCOPES = [
    # For using GMAIL API
    'https://www.googleapis.com/auth/gmail.modify',
    # For using Google sheets as CRM, can comment if using Airtable or other CRM
    'https://www.googleapis.com/auth/spreadsheets',
    # For saving files into Google Docs
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive"
]


def get_current_date():
    return datetime.now().strftime("%Y-%m-%d")

def get_google_credentials():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds
    
def get_report(reports, report_name: str):
    """
    Retrieves the content of a report by its title.
    """
    for report in reports:
        if report.title == report_name:
            return report.content
    return ""

def save_reports_locally(reports):
    # Define the local folder path
    reports_folder = "reports"
    
    # Create folder if it does not exist
    if not os.path.exists(reports_folder):
        os.makedirs(reports_folder)
    
    # Save each report as a file in the folder
    for report in reports:
        file_path = os.path.join(reports_folder, f"{report.title}.txt")
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(report.content)

def get_llm_by_provider(llm_provider, model):
    # Only Google Gemini is supported (free tier via AI Studio)
    if llm_provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(model=model, temperature=0.1)
    else:
        raise ValueError(f"Unsupported LLM provider: {llm_provider}. Only 'google' (Gemini) is supported in free mode.")
    return llm

def invoke_llm(
    system_prompt,
    user_message,
    model=None,  # reads from GEMINI_MODEL env var
    llm_provider="google",
    response_format=None
):
    if model is None:
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]  
    
    # Get base llm
    llm = get_llm_by_provider(llm_provider, model)
    
    # If Response format is provided the use structured output
    if response_format:
        llm = llm.with_structured_output(response_format)
    else: # Esle use parse string output
        llm = llm | StrOutputParser()
    
    # Invoke LLM
    output = llm.invoke(messages)
    
    return output


def invoke_llm_resilient(messages, temperature=0.1):
    """Invoke Gemini with auto-fallback across API keys AND models on 429/quota errors."""
    primary = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    models_to_try = [primary] + [m for m in FALLBACK_MODELS if m != primary]
    api_keys = _get_api_keys()
    last_err = None
    # Try every combination: key1+model1, key1+model2, ..., key2+model1, key2+model2, ...
    for api_key in api_keys:
        for model in models_to_try:
            try:
                kwargs = {"model": model, "temperature": temperature}
                if api_key:
                    kwargs["google_api_key"] = api_key
                llm = ChatGoogleGenerativeAI(**kwargs)
                result = llm.invoke(messages)
                return result
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                    key_hint = api_key[-6:] if api_key else "default"
                    print(f"⚠️ {model} (key ...{key_hint}) quota exhausted, trying next...")
                    last_err = e
                    continue
                raise  # Non-quota error — don't retry
    raise last_err  # All keys + models exhausted
