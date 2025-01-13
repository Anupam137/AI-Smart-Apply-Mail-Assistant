import streamlit as st
import logging
from dotenv import load_dotenv
import os
from langchain_community.document_loaders import WebBaseLoader

from chains import Chain
from portfolio import Portfolio
from utils import clean_text

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def validate_url(url):
    """Validate the input URL."""
    if not url.startswith(('http://', 'https://')):
        raise ValueError("Please enter a valid URL starting with http:// or https://")

def validate_portfolio_source(source):
    """Validate portfolio source (local file or URL)."""
    if not source:
        return None
    
    # Check if it's a URL
    if source.startswith(('http://', 'https://')):
        return source
    
    # Check if it's a local file
    if not os.path.exists(source):
        raise ValueError(f"Portfolio file not found: {source}")
    
    if not source.lower().endswith('.csv'):
        raise ValueError("Portfolio file must be a CSV")
    
    return source

def create_streamlit_app(llm, portfolio, clean_text):
    st.set_page_config(
        page_title="📧 Smart Apply Mail Assistant", 
        page_icon="📧", 
        layout="wide"
    )
    
    st.title("📧 Smart Apply Mail Assistant")
    st.markdown("""
    ### Generate Personalized Cold Emails for Job Applications
    
    This tool helps you create tailored cold emails by:
    - Extracting job details from a careers page
    - Matching your portfolio skills
    - Generating a personalized email
    """)
    
    # Load default URL from environment
    default_url = os.getenv('DEFAULT_JOB_URL', '')
    default_portfolio = os.path.join(os.path.dirname(__file__), "resource", "my_portfolio.csv")
    
    # User details section
    st.sidebar.header("👤 Your Details")
    user_name = st.sidebar.text_input(
        "Your Full Name", 
        placeholder="Enter your full name",
        help="This will be used in the personalized email"
    )
    
    # Portfolio source selection
    portfolio_source_type = st.radio(
        "Select Portfolio Source", 
        ["Local File", "URL", "Default"],
        help="Choose how you want to provide your portfolio"
    )
    
    # Portfolio source input based on selection
    custom_portfolio_source = None
    if portfolio_source_type == "Local File":
        uploaded_file = st.file_uploader(
            "Upload Portfolio CSV", 
            type=['csv'],
            help="Upload your portfolio CSV file"
        )
        if uploaded_file is not None:
            # Save uploaded file temporarily
            custom_portfolio_source = os.path.join(os.path.dirname(__file__), "resource", "uploaded_portfolio.csv")
            with open(custom_portfolio_source, "wb") as f:
                f.write(uploaded_file.getbuffer())
    elif portfolio_source_type == "URL":
        custom_portfolio_source = st.text_input(
            "Enter Portfolio CSV URL", 
            help="Paste a direct link to a publicly accessible CSV file"
        )
    else:
        st.info("Using default portfolio")
    
    # Job URL input
    url_input = st.text_input(
        "Enter Job Listing URL:", 
        value=default_url,
        help="Paste the URL of a job listing from a company's careers page"
    )
    
    # Sidebar configuration
    st.sidebar.header("⚙️ Configuration")
    max_links = st.sidebar.slider(
        "Max Portfolio Links", 
        min_value=1, 
        max_value=5, 
        value=int(os.getenv('MAX_PORTFOLIO_LINKS', 3))
    )
    
    submit_button = st.button("Generate Email")

    # Session state to store generated emails
    if 'generated_emails' not in st.session_state:
        st.session_state.generated_emails = []

    if submit_button:
        try:
            # Validate inputs
            validate_url(url_input)
            
            # Use default name if not provided
            if not user_name:
                user_name = "Applicant"
            
            # Portfolio source validation
            if custom_portfolio_source:
                custom_portfolio_source = validate_portfolio_source(custom_portfolio_source)
            
            # Load and process job listing
            loader = WebBaseLoader([url_input])
            data = clean_text(loader.load().pop().page_content)
            
            # Load portfolio (with optional custom source)
            portfolio.load_portfolio(custom_portfolio_source)
            
            # Extract job details
            jobs = llm.extract_jobs(data)
            
            # Clear previous generated emails
            st.session_state.generated_emails = []
            
            # Generate emails
            st.subheader("📧 Generated Emails")
            for job in jobs:
                skills = job.get('skills', [])
                links = portfolio.query_links(skills, n_results=max_links)
                
                # Generate email with user name and job URL
                email = llm.write_mail(job, links, user_name, url_input)
                
                # Store generated email in session state
                st.session_state.generated_emails.append({
                    'job': job.get('role', 'Job'),
                    'email': email
                })
        
        except ValueError as ve:
            st.error(f"Validation Error: {ve}")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)
            st.error(f"An unexpected error occurred. Please try again or check the URL. Error: {e}")
        finally:
            # Clean up temporary uploaded file if it exists
            if portfolio_source_type == "Local File" and custom_portfolio_source and os.path.exists(custom_portfolio_source):
                os.remove(custom_portfolio_source)

    # Display generated emails with editing capability
    if st.session_state.generated_emails:
        for idx, email_data in enumerate(st.session_state.generated_emails):
            with st.expander(f"Email for {email_data['job']} Position"):
                # Editable text area for the email
                edited_email = st.text_area(
                    f"Edit Email for {email_data['job']}", 
                    value=email_data['email'], 
                    height=300, 
                    key=f"email_edit_{idx}"
                )
                
                # Copy button
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"Copy Email for {email_data['job']}", key=f"copy_{idx}"):
                        st.clipboard.copy(edited_email)
                        st.success("Email copied to clipboard!")
                
                with col2:
                    # Option to save edited email
                    save_email = st.button(f"Save Edited Email", key=f"save_{idx}")
                    if save_email:
                        # You can implement additional save logic here if needed
                        st.success(f"Edited email for {email_data['job']} saved!")


if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Initialize components
    chain = Chain()
    portfolio = Portfolio()
    
    # Run the Streamlit app
    create_streamlit_app(chain, portfolio, clean_text)
