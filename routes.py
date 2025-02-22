import os
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from app.config import Config
from app.services import ats, adzuna_service, google_search_service
from app.models import db, User
main = Blueprint('main', __name__)

# Define the uploads folder and ensure it exists
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

### Existing endpoints go here (upload_resume, job_search, job_links, match_jobs_v2, etc.)

# ------------------------------
# User Signup Endpoint
# ------------------------------
@main.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Email and password are required."}), 400
    
    email = data.get('email')
    password = data.get('password')
    
    # Check if user already exists
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists."}), 400
    
    user = User(email=email)
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({"message": "User created successfully."}), 201

# ------------------------------
# User Login Endpoint
# ------------------------------
@main.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Email and password are required."}), 400
    
    email = data.get('email')
    password = data.get('password')
    
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        # In a real-world scenario, you might generate a session or JWT token here.
        return jsonify({"message": "Login successful."}), 200
    else:
        return jsonify({"error": "Invalid email or password."}), 401
    
    
@main.route('/upload_resume', methods=['POST'])
def upload_resume():
    if 'resume' not in request.files:
        return jsonify({"error": "No resume file provided"}), 400

    file = request.files['resume']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
    file.save(filepath)

    resume_text = ats.extract_text_from_pdf(filepath)
    job_description = request.form.get('job_description')
    if not job_description:
        return jsonify({"error": "Job description not provided"}), 400

    score = ats.calculate_ats_score(resume_text, job_description)
    suggestions = "Consider adding more relevant keywords based on the job description." if score < 50 else "Your resume is well optimized."
    
    return jsonify({
        "ats_score": score,
        "suggestions": suggestions
    })

@main.route('/job_search', methods=['GET'])
def job_search():
    keyword = request.args.get('keyword')
    location = request.args.get('location', '')
    if not keyword:
        return jsonify({"error": "Keyword parameter required"}), 400
    jobs = adzuna_service.get_jobs_by_keyword(keyword, location)
    return jsonify({"jobs": jobs})

@main.route('/match_jobs_v2', methods=['POST'])
def match_jobs_v2():
    # Get the user-provided job description (required)
    user_job_desc = request.form.get('job_description')
    if not user_job_desc:
        return jsonify({"error": "Job description is required"}), 400

    # Optionally process the resume if provided
    resume_text = None
    resume_keywords = set()
    if 'resume' in request.files:
        file = request.files['resume']
        if file.filename != '':
            filepath = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
            file.save(filepath)
            resume_text = ats.extract_text_from_pdf(filepath)
            resume_keywords = set(ats.preprocess_text(resume_text))
    
    # Build search query from the provided job description keywords
    user_job_keywords = set(ats.preprocess_text(user_job_desc))
    query = " ".join(list(user_job_keywords)[:5])  # using the top 5 keywords
    print("Search Query:", query)  # Debug print

    # Fetch jobs from Adzuna API using the query
    jobs = adzuna_service.get_jobs_by_keyword(query)
    print("Fetched Jobs:", jobs)  # Debug print

    matched_jobs = []
    for job in jobs:
        # Use the fetched job description if available; otherwise, fall back to an empty string.
        fetched_job_desc = job.get("description", "")
        print("Fetched Job Description:", fetched_job_desc)  # Debug print

        # Calculate ATS score comparing the user-provided job description with the fetched job description
        user_job_score = ats.calculate_ats_score(user_job_desc, fetched_job_desc)
        # Also compute an ATS score for the job title
        job_title = job.get("job_title", "")
        title_ats_score = ats.calculate_ats_score(user_job_desc, job_title)

        # Determine missing keywords: what's in the fetched job description but missing in the user's job description
        fetched_job_keywords = set(ats.preprocess_text(fetched_job_desc))
        missing_from_user = list(fetched_job_keywords - user_job_keywords)

        job_data = {
            "job_title": job_title,
            "title_ats_score": title_ats_score,
            "company": job.get("company"),
            "location": job.get("location"),
            "job_url": job.get("job_url"),
            "user_job_description_ats_score": user_job_score,
            "missing_keywords_in_user_job_description": missing_from_user
        }

        # If a resume was provided, also compare it with the fetched job description
        if resume_text:
            resume_job_score = ats.calculate_ats_score(resume_text, fetched_job_desc)
            missing_from_resume = list(fetched_job_keywords - resume_keywords)
            job_data["resume_job_ats_score"] = resume_job_score
            job_data["missing_keywords_in_resume"] = missing_from_resume

        # Optionally fetch extra job links via Google Search API and compute ATS scores for each link's snippet.
        extra_links = google_search_service.get_job_links(job_title, job.get("location"))
        for link in extra_links:
            snippet = link.get("snippet", "")
            # Compute an ATS score for the snippet (do not output the snippet's keywords)
            link["ats_score"] = ats.calculate_ats_score(user_job_desc, snippet)
        job_data["extra_links"] = extra_links

        print("Job Data:", job_data)  # Debug print
        matched_jobs.append(job_data)

    return jsonify({
        "query_used": query,
        "matched_jobs": matched_jobs
    })
