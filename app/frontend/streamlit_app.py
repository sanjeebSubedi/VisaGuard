"""
VisaGuard Streamlit Frontend

A chat-based interface for F-1 OPT compliance assistance.

Features:
- Document upload (PDF ingestion)
- Conversational interface
- Compliance status dashboard
- Form generation workflow with HITL
"""

import streamlit as st
from pathlib import Path
import tempfile
from datetime import date
import json

# Page config
st.set_page_config(
    page_title="VisaGuard - F-1 OPT Compliance Assistant",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }
    .main-header {
        background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 700;
    }
    .status-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 0.5rem 0;
    }
    .status-compliant {
        border-left: 4px solid #10b981;
    }
    .status-warning {
        border-left: 4px solid #f59e0b;
    }
    .status-violation {
        border-left: 4px solid #ef4444;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 12px;
        margin: 0.5rem 0;
    }
    .user-message {
        background: rgba(79, 70, 229, 0.2);
        border: 1px solid rgba(79, 70, 229, 0.3);
    }
    .assistant-message {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "documents" not in st.session_state:
        st.session_state.documents = []
    if "compliance_status" not in st.session_state:
        st.session_state.compliance_status = None
    if "student_data" not in st.session_state:
        st.session_state.student_data = {}
    if "employer_data" not in st.session_state:
        st.session_state.employer_data = {}
    if "training_plan" not in st.session_state:
        st.session_state.training_plan = {}
    if "awaiting_approval" not in st.session_state:
        st.session_state.awaiting_approval = False
    if "timeline_data" not in st.session_state:
        st.session_state.timeline_data = None


def render_sidebar():
    """Render the sidebar with status and settings."""
    with st.sidebar:
        st.markdown("## 🛡️ VisaGuard")
        st.markdown("*F-1 OPT Compliance Assistant*")
        st.divider()
        
        # Status Summary
        st.markdown("### 📊 Status Overview")
        
        # Timeline Status
        timeline = st.session_state.timeline_data
        if timeline:
            unemployment_days = timeline.get("unemployment_days", 0)
            unemployment_limit = timeline.get("unemployment_limit", 90)
            days_remaining = unemployment_limit - unemployment_days
            
            st.metric(
                "Unemployment Days",
                f"{unemployment_days}/{unemployment_limit}",
                f"{days_remaining} remaining",
                delta_color="inverse" if days_remaining < 30 else "normal"
            )
            
            warning_level = timeline.get("warning_level", "none")
            if warning_level == "critical":
                st.error("⚠️ Critical: Act immediately")
            elif warning_level == "warning":
                st.warning("⚡ Warning: Monitor closely")
            elif warning_level == "violation":
                st.error("🚨 VIOLATION: Seek legal advice")
            else:
                st.success("✅ On track")
        else:
            st.info("No timeline data yet")
        
        st.divider()
        
        # Document Upload
        st.markdown("### 📄 Upload Documents")
        uploaded_file = st.file_uploader(
            "Upload PDF",
            type=["pdf"],
            help="Upload I-20, I-983, EAD card, etc."
        )
        
        if uploaded_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = Path(tmp.name)
            
            # Process document
            with st.spinner("Processing document..."):
                try:
                    from app.services.ingestion import get_ingestion_service
                    service = get_ingestion_service()
                    doc = service.ingest_pdf(tmp_path)
                    
                    st.session_state.documents.append({
                        "name": uploaded_file.name,
                        "id": doc.document_id,
                        "hash": doc.content_hash[:8],
                    })
                    st.success(f"✅ Uploaded: {uploaded_file.name}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        
        # List uploaded documents
        if st.session_state.documents:
            st.markdown("**Uploaded:**")
            for doc in st.session_state.documents:
                st.markdown(f"- 📄 {doc['name']}")
        
        st.divider()
        
        # Quick Actions
        st.markdown("### ⚡ Quick Actions")
        
        if st.button("🔍 Check Compliance", use_container_width=True):
            st.session_state.messages.append({
                "role": "user",
                "content": "Check my current compliance status"
            })
            st.rerun()
        
        if st.button("📝 Generate I-983", use_container_width=True):
            st.session_state.messages.append({
                "role": "user",
                "content": "Help me generate an I-983 Training Plan"
            })
            st.rerun()
        
        if st.button("❓ Policy Question", use_container_width=True):
            st.session_state.messages.append({
                "role": "user",
                "content": "What are the STEM OPT unemployment rules?"
            })
            st.rerun()


def render_chat():
    """Render the main chat interface."""
    st.markdown('<h1 class="main-header">VisaGuard Assistant</h1>', unsafe_allow_html=True)
    st.markdown("Your AI-powered F-1 OPT compliance companion")
    st.divider()
    
    # Display chat messages
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            role = message["role"]
            content = message["content"]
            
            if role == "user":
                with st.chat_message("user"):
                    st.markdown(content)
            else:
                with st.chat_message("assistant", avatar="🛡️"):
                    st.markdown(content)
    
    # Approval buttons (if awaiting)
    if st.session_state.awaiting_approval:
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("✅ Approve", type="primary", use_container_width=True):
                st.session_state.messages.append({
                    "role": "user",
                    "content": "Approve"
                })
                st.session_state.awaiting_approval = False
                st.rerun()
        with col2:
            if st.button("❌ Reject", use_container_width=True):
                st.session_state.messages.append({
                    "role": "user",
                    "content": "Reject - I need to make changes"
                })
                st.session_state.awaiting_approval = False
                st.rerun()
    
    # Chat input
    if prompt := st.chat_input("Ask about OPT compliance, regulations, or forms..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Process message
        with st.spinner("Thinking..."):
            response = process_message(prompt)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()


def process_message(user_message: str) -> str:
    """
    Process user message and generate response.
    
    In production, this would invoke the LangGraph workflow.
    For MVP, we provide direct responses.
    """
    message_lower = user_message.lower()
    
    # Handle approval responses
    if any(word in message_lower for word in ["approve", "yes", "confirm"]):
        return (
            "✅ **Form Generation Approved**\n\n"
            "Your I-983 Training Plan is being generated. "
            "You'll receive a download link shortly.\n\n"
            "*Note: In production, this would generate the actual PDF.*"
        )
    
    if any(word in message_lower for word in ["reject", "no", "cancel"]):
        return (
            "❌ **Form Generation Cancelled**\n\n"
            "No problem! Let me know what changes you'd like to make, "
            "or if you have any questions about the form."
        )
    
    # Policy questions
    if "unemployment" in message_lower or "how many days" in message_lower:
        return (
            "## F-1 OPT Unemployment Rules\n\n"
            "According to **8 CFR 214.2(f)(10)(ii)(E)**:\n\n"
            "- **Post-Completion OPT**: Maximum **90 days** of unemployment\n"
            "- **STEM OPT Extension**: Maximum **150 days** total (cumulative)\n\n"
            "⚠️ **Important:**\n"
            "- Unemployment is counted from your OPT start date\n"
            "- Working less than 20 hours/week counts as unemployment\n"
            "- Self-employment is NOT allowed during STEM OPT\n\n"
            "*Do you have a specific situation you'd like me to analyze?*"
        )
    
    # Compliance check
    if "compliance" in message_lower or "status" in message_lower:
        # Simulate timeline calculation
        st.session_state.timeline_data = {
            "unemployment_days": 45,
            "unemployment_limit": 90,
            "warning_level": "none",
            "days_until_opt_end": 180,
        }
        
        return (
            "## 📊 Compliance Status Check\n\n"
            "Based on your current data:\n\n"
            "| Metric | Value | Status |\n"
            "|--------|-------|--------|\n"
            "| Unemployment Days | 45/90 | ✅ OK |\n"
            "| OPT Days Remaining | 180 | ✅ Active |\n"
            "| E-Verify Status | Verified | ✅ Valid |\n\n"
            "### Recommendations:\n"
            "- ✅ You're currently in good standing\n"
            "- 📅 Next reporting deadline: 30 days\n"
            "- 💡 Consider uploading your latest pay stub for records\n\n"
            "*Is there anything specific you'd like me to check?*"
        )
    
    # I-983 generation
    if "i-983" in message_lower or "training plan" in message_lower:
        st.session_state.awaiting_approval = True
        
        return (
            "## 📝 I-983 Training Plan Generator\n\n"
            "I'll help you create your I-983 form. First, let me show you "
            "what information I have:\n\n"
            "### Student Information\n"
            "- **Name**: Not yet provided\n"
            "- **SEVIS ID**: Not yet provided\n"
            "- **School**: Not yet provided\n\n"
            "### Employer Information\n"
            "- **Company**: Not yet provided\n"
            "- **EIN**: Not yet provided\n\n"
            "### Training Plan\n"
            "- **Start Date**: Not yet provided\n"
            "- **Hours/Week**: Not yet provided\n\n"
            "---\n"
            "❓ **Missing Information**\n\n"
            "To generate your I-983, please provide:\n"
            "1. Your student information (or upload your I-20)\n"
            "2. Employer details (or upload your offer letter)\n"
            "3. Training plan goals and supervisor info\n\n"
            "*Would you like to fill these in now, or upload documents?*"
        )
    
    # Default response
    return (
        "I'm here to help with F-1 OPT compliance! Here's what I can do:\n\n"
        "- 🔍 **Check Compliance**: Analyze your current status\n"
        "- 📝 **Generate Forms**: Create I-983 Training Plans\n"
        "- ❓ **Answer Questions**: Explain OPT regulations\n"
        "- 📅 **Track Deadlines**: Monitor reporting requirements\n\n"
        f"You asked: *\"{user_message}\"*\n\n"
        "Could you clarify what you'd like help with?"
    )


def render_data_entry_modal():
    """Render data entry forms in expandable sections."""
    with st.expander("📋 Enter Student Information", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("First Name")
            sevis_id = st.text_input("SEVIS ID", placeholder="N0012345678")
            school = st.text_input("School Name")
        with col2:
            last_name = st.text_input("Last Name")
            email = st.text_input("Email")
            major = st.text_input("Major (CIP Code)")
        
        if st.button("Save Student Info"):
            st.session_state.student_data = {
                "first_name": first_name,
                "last_name": last_name,
                "sevis_id": sevis_id,
                "email": email,
                "school_name": school,
                "major_cip": major,
            }
            st.success("✅ Student information saved!")
    
    with st.expander("🏢 Enter Employer Information", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            company = st.text_input("Company Name")
            street = st.text_input("Street Address")
            city = st.text_input("City")
        with col2:
            ein = st.text_input("EIN", placeholder="12-3456789")
            state = st.text_input("State")
            zip_code = st.text_input("ZIP Code")
        
        if st.button("Save Employer Info"):
            st.session_state.employer_data = {
                "company_name": company,
                "street": street,
                "city": city,
                "state": state,
                "zip": zip_code,
                "ein": ein,
            }
            st.success("✅ Employer information saved!")


def main():
    """Main application entry point."""
    init_session_state()
    
    # Layout
    render_sidebar()
    
    # Main content
    col1, col2 = st.columns([3, 1])
    
    with col1:
        render_chat()
    
    with col2:
        render_data_entry_modal()


if __name__ == "__main__":
    main()
