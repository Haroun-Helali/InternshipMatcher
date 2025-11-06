"""Create sample PDF files for testing."""
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def create_sample_internship_pdf():
    """Create a sample internship PDF for testing."""
    pdf_path = Path(__file__).parent / "sample_internship.pdf"
    
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    width, height = letter
    
    # Page 1
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, height - 100, "Software Engineering Internship")
    
    c.setFont("Helvetica", 12)
    y = height - 140
    
    content = [
        "Company: Tech Innovations Inc.",
        "Location: San Francisco, CA (Hybrid)",
        "Duration: Summer 2025 (12 weeks)",
        "",
        "About the Role:",
        "We are seeking a talented software engineering intern to join our team.",
        "You will work on real-world projects using modern technologies including",
        "Python, React, and cloud infrastructure.",
        "",
        "Requirements:",
        "- Currently pursuing a degree in Computer Science or related field",
        "- Strong programming skills in Python or JavaScript",
        "- Understanding of data structures and algorithms",
        "- Excellent problem-solving abilities",
        "- Good communication skills",
        "",
        "Preferred Qualifications:",
        "- Experience with web frameworks (FastAPI, Django, Flask, or Express)",
        "- Familiarity with React or Vue.js",
        "- Knowledge of Git and version control",
        "- Previous internship or project experience",
        "",
        "What You'll Learn:",
        "- Full-stack web development",
        "- Cloud deployment and DevOps practices",
        "- Agile development methodologies",
        "- Code review and collaboration best practices",
    ]
    
    for line in content:
        c.drawString(100, y, line)
        y -= 20
        if y < 100:  # Start new page
            c.showPage()
            c.setFont("Helvetica", 12)
            y = height - 100
    
    # Page 2
    c.showPage()
    c.setFont("Helvetica", 12)
    y = height - 100
    
    more_content = [
        "Benefits:",
        "- Competitive hourly rate ($25-35/hour based on experience)",
        "- Mentorship from senior engineers",
        "- Flexible work schedule",
        "- Professional development opportunities",
        "- Free lunch and snacks",
        "",
        "Application Process:",
        "1. Submit your resume and cover letter",
        "2. Complete a coding challenge",
        "3. Technical interview with the team",
        "4. Final interview with hiring manager",
        "",
        "To Apply:",
        "Send your application to: internships@techinnovations.com",
        "Application Deadline: December 15, 2024",
        "",
        "We are an equal opportunity employer and value diversity.",
    ]
    
    for line in more_content:
        c.drawString(100, y, line)
        y -= 20
    
    c.save()
    print(f"Created sample PDF: {pdf_path}")


def create_malformed_pdf():
    """Create a malformed PDF for error testing."""
    pdf_path = Path(__file__).parent / "malformed.pdf"
    
    # Write invalid PDF content
    with open(pdf_path, 'w') as f:
        f.write("This is not a valid PDF file")
    
    print(f"Created malformed PDF: {pdf_path}")


def create_empty_pdf():
    """Create an empty PDF for testing."""
    pdf_path = Path(__file__).parent / "empty.pdf"
    
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    # Don't add any content, just save
    c.save()
    
    print(f"Created empty PDF: {pdf_path}")


if __name__ == "__main__":
    create_sample_internship_pdf()
    create_malformed_pdf()
    create_empty_pdf()
    print("All sample PDFs created successfully!")
