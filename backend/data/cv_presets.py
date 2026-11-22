from __future__ import annotations

# Real candidate reference CVs used for preset switching, ATS parsing regression checks,
# and instant testing across diverse tech, data, consulting, AI, and ops roles.

CV_PRESETS: dict[str, dict[str, str]] = {
    "stripe_data_analyst": {
        "id": "stripe_data_analyst",
        "label": "Stripe Data Analyst Intern CV",
        "filename": "Mbesa_Lephoto_Stripe_Data_Analyst_Intern_CV.pdf",
        "default_company": "Stripe",
        "default_role": "Data Analyst Intern",
        "default_jd": (
            "Own high-impact payments, risk/fraud, and financial analytics deliverables end-to-end. "
            "Build scalable SQL and Python data pipelines, design metrics semantic layers and executive "
            "dashboards, analyze conversion and return friction, and partner with product and engineering teams."
        ),
        "raw_text": """MBESA LEPHOTO
072 880 8192 | tlephoto14@gmail.com | LinkedIn | GitHub | Johannesburg, South Africa (Open to International Relocation & Visa Sponsorship) | South African Citizen

PROFESSIONAL SUMMARY
Analytical, ambitious builder pursuing a quantitative BSc in Information Technology: Software Engineering (82.4% average across 19 passed modules, 14 distinctions | Expected Graduation: December 2027). Experienced in SQL (93% Distinction - 100% Final Exam), Python (91% Distinction), building scalable data pipelines, designing metrics semantic layers and executive dashboards (Microsoft Power BI, React/Recharts), and leveraging AI tools to accelerate analysis, modeling, and code validation. Passionate about programmable financial infrastructure, payments, and risk/fraud analytics, with hands-on projects spanning distributed payment processing (Lightning Webstore), real-time anti-spoofing risk scoring (VoiceGuard), and multi-table financial/supply-chain analytics. Ready to own high-impact analytics deliverables end to end as a Data Analyst, Intern at Stripe.

EDUCATION
Bachelor of Science in Information Technology: Software Engineering
Eduvos (DHET Accredited Higher Education Institution, SAQA ID: 120690), South Africa | 2024 - Expected Graduation: December 2027
• Cumulative Standing: 82.4% Average across 19 Passed Modules | 14 Distinctions (75%+ SA Distinction Scale) | Top 3 Cohort Achiever
• Quantitative, Data & Systems Coursework: Introduction to Information Systems (97%), Database Systems (93%, 100% Final Exam), Programming in Python (91%), Mathematics 1B (80%), Mathematics for Computing (77%), Computer Network and Security (96%), AI Ethics and Privacy (86%), Non-Technical Skills for IT Professionals (94%), Usability Engineering (81%)
Systems and Design Qualification (MICTSETA National Occupational Programme) | Completed 2024
National Senior Certificate (Bachelor's Degree Pass) | Rustenburg Educational College | Class of 2022

DATA ANALYTICS, PIPELINES & TECHNICAL SKILLS
• SQL & Data Modeling: SQL (Microsoft SQL Foundations, PostgreSQL, MySQL, SQLite WAL mode), Star Schema Dimensional Modeling, Relational Normalization, Data Access Object (DAO) Pattern, Parameterized Queries
• Metrics Semantic Layers & BI: Microsoft Power BI (Power Query M ETL, DAX Measures: CALCULATE, DATESYTD, SAMEPERIODLASTYEAR, TOPN, AVERAGEX), React & Recharts Analytics (MetricPoint[]), Microsoft Excel, Data Storytelling & Executive Recommendations
• Data Pipelines & Python: Python 3.12 (FastAPI, Flask, NumPy, Pytest, Automation Scripting), Multi-Source Data Ingestion, Streaming Sliding-Window Pipelines, Regex Sanitization & Pipeline Debugging
• AI-Accelerated Development & Risk Modeling: ChatGPT, Claude, GitHub Copilot, PyTorch, ONNX, Cosine Similarity & Exponential Moving Average (EMA) Risk Scoring
• Payments & Engineering Stack: Distributed Payment APIs, Docker & Docker Compose, Git/GitHub, Linux Operating Systems, AWS Concepts

DATA ANALYTICS, PIPELINE & PAYMENTS PROJECTS
Enterprise Metrics Semantic Layer & BI Solution | Microsoft Power BI, Power Query, DAX
• Cleaned and validated five operational datasets (Financials, HR, Sales, Inventory, and Supplier) in Power Query (Text.Clean, Text.Trim, Text.Proper, locale typing) to achieve 100% zero-error data assets.
• Built a dimensional Star Schema (Date, DimProduct, DimSupplier, DimCustomer) and standardized a reusable DAX metrics semantic layer (Net Sales after Returns, Net Income YTD, Gross Profit Margin %, Current Ratio, Weighted Supplier Performance Score, and Top 10 Customer Revenue).
• Delivered an executive data storytelling report diagnosing liquidity shifts (Current Ratio 1.20 to 1.17), 771 critical stockout risks, 1.03% regional return friction, and vendor reliability risk, formulating concrete strategic recommendations.

VoiceGuard: Real-Time Risk Scoring & Streaming Data Pipeline (voice-guard) | Python, PyTorch, ONNX, WebSockets
• Designed and debugged a low-latency CPU streaming data pipeline chunking 16 kHz audio into overlapping windows (4s window, 0.75s hop) across a multi-stage fallback transformation chain.
• Combined neural anti-spoofing inference (RawNet2/ONNX) with spectral statistical heuristics and Exponential Moving Average (EMA) smoothing to output calibrated 0 to 100% fraud/synthetic-voice risk scores.

VeriFace AI: Multi-Source Data Ingestion & Vector Retrieval Pipeline (face-check) | Python, FastAPI, Qdrant, SQLite (WAL), NumPy
• Engineered an async concurrent ingestion pipeline querying external web APIs, normalizing geometry via closed-form NumPy SVD, and persisting 512-D embeddings across SQLite (WAL mode) and Qdrant with pytest pipeline validation.

Lightning Webstore (Programmable Payment Processing Integration) | Python, Flask, REST APIs, SQL
• Built a fault-tolerant payment application integrating decentralized payment rails, focusing on transaction reliability, checkout API error handling, and rigorous SQL database validation.

Lowkey AI: AI Output Validation & Pipeline Debugging | Python, TypeScript, Regex
• Developed a post-processing Python pipeline with regex sanitization and length-ratio heuristics to validate AI outputs, flag anomalies, and execute automated retries.

WORK & COLLABORATIVE EXPERIENCE
Freelance Analytics & Software Builder | Self-Employed | 2025 - 2026
• Partnered directly with stakeholders to define core business metrics and shipped a modular React and TypeScript (MetricPoint[], Recharts) analytics dashboard under a strict 2-week MVP deadline to secure investor funding.
IT Systems & Operations Intern | Quarphix | Jul 2024 - Jan 2025
• Automated bulk cloud account provisioning and session revocation via Python (secrets CSPRNG) and REST APIs, eliminating manual operational toil by 40+ hours per month.
ICT Youth Development Intern | Sci-Bono Discovery Centre | Mar 2025 - Aug 2025
• Engineered Python data processing scripts to eliminate repetitive manual entry errors and improve internal record accuracy.
Virtual Java Programming Intern | HexSoftwares | Mar 2026 - Apr 2026
• Collaborated in structured code reviews, incorporating mentor and peer feedback to strengthen code quality and maintainability.

LEADERSHIP & CERTIFICATIONS
• Deputy President, Eduvos IT Coding Club (2024 - Present): Mentor junior undergraduate peers weekly in SQL, Python, and structured debugging.
• Verified Certifications: SQL Foundations (Microsoft) | Python for Data Science, AI & Development (IBM) | Machine Learning with Python (IBM) | Neural Networks and Deep Learning (DeepLearning.AI) | AWS AI Practitioner Challenge & AWS AI & ML Scholars Challenge 2026 (Udacity) | Foundations of Cybersecurity (Google)""",
    },
    "amazon_sde_sa": {
        "id": "amazon_sde_sa",
        "label": "Amazon SA SDE Intern CV",
        "filename": "Mbesa_Lephoto_Amazon_SA_SDE_CV.pdf",
        "default_company": "Amazon",
        "default_role": "Software Development Engineer Intern",
        "default_jd": (
            "Design and build scalable, cloud-native distributed systems on AWS. Demonstrate strong CS "
            "fundamentals (data structures, algorithms, OOP), full software development lifecycle ownership, "
            "clean maintainable code, CI/CD, and Amazon Leadership Principles."
        ),
        "raw_text": """THUTO LEPHOTO
072 880 8192 | tlephoto14@gmail.com | LinkedIn | GitHub | Midrand, Gauteng | South African Citizen | Open to relocate (Stellenbosch, Century City, Sandton)

PROFESSIONAL SUMMARY
Customer-obsessed and highly analytical Software Engineering student (82% academic average) passionate about designing and building scalable, cloud-native solutions. Equipped with a strong foundation in Computer Science fundamentals (data structures, algorithms, and object-oriented design), distributed systems, modern GenAI technologies, and operational excellence through hands-on internships and independent projects. Adept at taking ownership of the full software development lifecycle from technical design through to CI/CD deployment while writing clean, maintainable code and critically validating AI-assisted outputs. Eager to solve complex, real-world customer problems and drive innovation as a Software Development Engineer Intern / SDE at Amazon.

EDUCATION
BSc Information Technology (Software Engineering) | Eduvos | 2024 - 2027 (Expected Graduation: November 2027)
• Accomplishments: Top 3 Achiever (82% Academic Average)
• Relevant Coursework: Data Structures & Algorithms, Object-Oriented Design, System Design, Database Architecture, AI Fundamentals, Distributed Computing Concepts
Learnership in Systems and Design | MICTSETA | Completed 2024

COMPETENCIES & TECHNICAL SKILLS
• Programming Languages: Python, Java (OOP), TypeScript, JavaScript, SQL, HTML/CSS
• CS Fundamentals & Architecture: Data Structures Implementation, Algorithm Development, Object-Oriented Design Principles, Problem Decomposition, REST APIs, Microservices, Flask apps
• Cloud & Infrastructure: Amazon Web Services (AWS), Docker, Kubernetes, OpenShift, Git Version Control, Agile & CI/CD Principles, SQL & NoSQL Databases
• GenAI & AI-Assisted Development: AI-Assisted Coding & Code Validation, Large Language Models (LLMs), Scikit-learn, Generative AI applications

WORK EXPERIENCE
Virtual Java Programming Intern | HexSoftwares | Mar 2026 - Apr 2026
• Acted as a code owner to design and develop functional Java application modules, applying object-oriented design patterns and data structures to contribute to wider software architectures.
Freelance Software Developer | Self-Employed | 2025 - 2026
• Architected a layout-agnostic React analytics dashboard under a strict 2-week MVP deadline to secure client investor funding using strict TypeScript interfaces (MetricPoint[]) and Recharts.
IT Systems & Operations Intern | Quarphix | Jul 2024 - Jan 2025
• Engineered a secure Python identity lifecycle automation script using the secrets module (CSPRNG) and automated bulk cloud account provisioning via REST APIs and instant session revocation, saving the team 40+ hours a month.
ICT Youth Development Programme Intern | Sci-Bono Discovery Centre | Mar 2025 - Aug 2025
• Leveraged Python to develop automation tools, eliminating operational bottlenecks and enhancing development productivity.

PROJECT EXPERIENCE
Lowkey AI: Evaluative Chatbot Platform | Python, TypeScript, CSS, Git
• Developed a robust post-processing Python pipeline to critically validate, sanitize, and correct flawed or truncated LLM and ZeroGPT API outputs with regex sanitization layers and length-ratio heuristics triggering automated graceful API retries.
Python Quiz & SQLite Leaderboard | Python, SQLite, Tkinter
• Built a desktop GUI integrated with a local SQLite database utilizing the Data Access Object (DAO) architecture, context managers, and parameterized queries (?) to defend against SQL injection.
Lightning Webstore (Distributed Ledger Integration) | Python, Flask, REST APIs, SQL
• Built and maintained fault-tolerant backend microservices interacting with the decentralized Lightning Network, executing rigorous database testing.
Library Management System | Java, OOP
• Developed an efficient, object-oriented application implementing custom data structures and design patterns for scalable data retrieval.

CERTIFICATIONS
• AWS & Cloud Architecture: AWS AI Practitioner Challenge (Udacity) | AWS AI & ML Scholars Challenge 2026 (Udacity) | Intro to Containers w/ Docker, Kubernetes & OpenShift (IBM)
• GenAI & Machine Learning: Machine Learning with Python (IBM) | Generative AI: Intro and Applications (IBM) | Neural Networks and Deep Learning (DeepLearning.AI)
• Core Tech: Intro to Software Engineering (IBM) | Intro to DevOps (IBM) | Foundations of Cybersecurity (Google) | SQL Foundations (Microsoft)""",
    },
    "bbd_grad_swe": {
        "id": "bbd_grad_swe",
        "label": "BBD Software Engineering Grad CV",
        "filename": "Mbesa_Lephoto_BBD_Software_Eng_Grad_CV.pdf",
        "default_company": "BBD",
        "default_role": "Graduate Software Engineer",
        "default_jd": (
            "Join BBD's Software Engineering Graduate Programme building bespoke enterprise software across "
            "financial services, banking, and digital platforms. Requires strong Computer Science fundamentals "
            "in Java or C#, OOP, relational databases (SQL), full-stack web dev, Git, and agile teamwork."
        ),
        "raw_text": """MBESA LEPHOTO
0728808192 | tlephoto14@gmail.com | Midrand, Gauteng

PROFESSIONAL SUMMARY
Passionate Software Engineering student immersed in technology over and above formal education, with a strong drive to build software that solves real-world problems. Adept at full-stack development, from modern front-end frameworks to backend databases, with a focus on clean architecture and secure-by-design principles. Eager to bring technical curiosity, client-delivery mindset, and collaborative energy to the BBD Software Engineering Grad Programme.

EDUCATION
BSc Information Technology (Software Engineering) | Eduvos | 2024 - Present (Expected Graduation: November 2026)
• Accomplishments: Top 3 Achiever (Year 1)
• Relevant Coursework: Database Systems, System Design, AI Fundamentals, Project Management
Learnership in Systems and Design | MICSETA | Completed 2024

TECHNICAL SKILLS
• Software Engineering: Java (OOP), Python, TypeScript, JavaScript, HTML, CSS
• Databases & Architecture: SQL, Database Architecture, System Design, REST APIs, Application Architecture
• DevOps & Quality: Git Version Control, Agile Ceremonies, Testing Fundamentals, Secure-by-Design Thinking
• Professional Competencies: Creative Problem Solving, Client Delivery Focus, Continuous Learning, Collaboration

WORK EXPERIENCE
Freelance Web Developer | Self-Employed | 2025 - 2026
• Built meaningful features and solved real-world problems by designing full-stack web applications for clients using modern frameworks and secure-by-design third-party APIs.
IT Support Programme Intern | Quarphix | Jul 2024 - Jan 2025
• Diagnosed and solved complex software and hardware issues, engineered technical training guides, and monitored user workflows.
Virtual Java Programming Intern | HexSoftwares | Mar 2026 - Apr 2026
• Collaborated within a delivery team to build, test, and ship functional Java application modules in agile ceremonies and code reviews.
ICT Youth Development Programme Intern | Sci-Bono Discovery Centre | Mar 2025 - Aug 2025
• Conceptualized and wrote Python scripts to automate repetitive tasks and improve efficiency.

PROJECTS
Lightning Webstore | Python, Flask, REST APIs, SQL | 2026
• Engineered a secure, full-stack web application managing decentralized Lightning Network payments with clean architecture and backend database testing.
Lowkey AI: Evaluative Chatbot Platform | TypeScript, CSS, Git | 2026
• Designed a platform to evaluate AI interactions securely with modern front-end state management.
Library Management System | Java, OOP | 2026
• Developed an interactive Java application implementing Object-Oriented design patterns.
Doomscroll Tracking System: Computer Vision Prototype | Python | 2026
• Conceptualized a computer vision script utilizing facial mesh tracking.

UNIVERSITY LEADERSHIP & COMMUNITY IMPACT
• Deputy President, Eduvos IT Coding Club: Facilitated group coding projects and curated technical workshops.
• Deputy Head Boy / SRC Deputy President, High School: Conflict resolution, meticulous planning, relationship building.

CERTIFICATIONS
• Introduction to Data Engineering (IBM) | Python for Data Science, AI & Development (IBM) | SQL Foundations (Microsoft) | Foundations of Cybersecurity (Google) | Introduction to Software Engineering (IBM) | Neural Networks and Deep Learning (DeepLearning.AI)""",
    },
    "boxfusion_grad_swe": {
        "id": "boxfusion_grad_swe",
        "label": "Boxfusion SWE Graduate CV",
        "filename": "Mbesa_Lephoto_Boxfusion_SWE_Grad_CV.pdf",
        "default_company": "Boxfusion",
        "default_role": "Software Engineering Graduate",
        "default_jd": (
            "Graduate Software Engineer working on enterprise and public-sector digital platforms using "
            "OOP (C#/.NET/Java), SQL Server / PostgreSQL, React, TypeScript, clean architecture, automated "
            "testing, and strong attention to detail."
        ),
        "raw_text": """MBESA LEPHOTO
072 880 8192 | tlephoto14@gmail.com | Midrand, Gauteng | South African Citizen

PROFESSIONAL SUMMARY
Highly motivated and analytical final-year BSc Information Technology (Software Engineering) student (82% academic average, Top 3 Achiever), locally based in Midrand and seeking my first formal IT career opportunity through Boxfusion's Software Engineering Graduate Programme. Equipped with a strong academic foundation in Object-Oriented Programming (Java/C# transferable principles), Data Structures, Relational Databases (SQL), and full-stack development across React, TypeScript, and Python. Eager to master .NET, Shesha, and complete Microsoft Certifications while growing alongside Boxfusion's engineering teams.

EDUCATION & ACCREDITED TRAINING
BSc Information Technology (Software Engineering) | Eduvos | 2024 - Present (SAQA ID: 120690, NQF 7)
• Academic Aggregate: 82% Average across (14 Distinctions | Top 3 Achiever)
Learnership in Systems and Design | MICTSETA | Completed 2024

COMPETENCIES & TECHNICAL SKILLS
• Core Programming & OOP: Java (OOP, Design Patterns, SOLID Principles), Python, TypeScript, JavaScript, SQL, HTML5/CSS3
• Frontend & Full-Stack Frameworks: React, Next.js 15, Tailwind CSS, Modular UI Architecture (MetricPoint[], Recharts), FastAPI, Flask, RESTful APIs
• Databases, Testing & Security: SQL (Microsoft SQL Foundations, PostgreSQL, MySQL, SQLite WAL mode), Data Access Object (DAO) Pattern, Parameterized Queries, pytest Unit & Pipeline Testing
• Cloud, DevOps & Productivity: Docker & Docker Compose, Kubernetes Foundations, AWS, Git & GitHub

ACADEMIC & INDEPENDENT SOFTWARE PROJECTS
VeriFace AI: Full-Stack Biometric Discovery Engine (face-check) | Next.js 15, React 19, TypeScript, Python, FastAPI, Docker
• Engineered a full-stack web application featuring a Next.js / TypeScript frontend integrated with an async Python FastAPI backend and containerized via Docker Compose, with SQLite (WAL mode), Qdrant, and pytest verification.
Modular Analytics Dashboard (Independent UI/UX Project) | React, TypeScript, Recharts
• Architected a layout-agnostic React analytics dashboard on a strict 2-week build cycle using strict TypeScript interfaces (MetricPoint[]).
VoiceGuard: Real-Time Audio Detection Pipeline (voice-guard) | Python, PyTorch, ONNX, WebSockets
• Built a multi-stage processing pipeline with live WebSocket telemetry, configurable thresholds (config.yaml), graceful fallback gates, and automated testing scripts.
Lowkey AI: Output Validation & Sanitization Pipeline | Python, TypeScript, CSS, Git
• Engineered a post-processing Python pipeline with regex sanitization layers and length-ratio heuristics to validate API outputs and trigger automated graceful retries.
Python Quiz & SQLite Leaderboard | Python, SQLite, Tkinter
• Developed a desktop application integrated with SQLite using the DAO architecture, context managers, and parameterized SQL queries (?) to prevent SQL injection.
Library Management System (Enterprise OOP) | Java, OOP
• Built an object-oriented software application demonstrating encapsulation, inheritance, polymorphism, and clean layered code standards.
Lightning Webstore (Distributed Ledger Integration) | Python, Flask, REST APIs, SQL
• Developed fault-tolerant backend microservices executing structured database validation for reliable financial record handling.

CERTIFICATIONS
• SQL Foundations (Microsoft) | Intro to Software Engineering (IBM) | Intro to DevOps (IBM) | Intro to Containers w/ Docker, Kubernetes & OpenShift (IBM) | Foundations of Cybersecurity (Google) | AWS AI & ML Scholars Challenge 2026 (Udacity)""",
    },
    "deloitte_infinityx": {
        "id": "deloitte_infinityx",
        "label": "Deloitte InfinityX Tech Consulting CV",
        "filename": "Mbesa_Lephoto_Deloitte_InfinityX_CV.pdf",
        "default_company": "Deloitte",
        "default_role": "Technology Consulting Graduate (InfinityX)",
        "default_jd": (
            "Launch a consulting career in Technology & Transformation with Deloitte's InfinityX Graduate "
            "Programme. Partner with enterprise clients on digital transformation, business process mapping, "
            "data analytics, software integration, risk analysis, and executive stakeholder communication."
        ),
        "raw_text": """MBESA LEPHOTO
0728808192 | tlephoto14@gmail.com | Midrand, Gauteng

PROFESSIONAL SUMMARY
Analytical and self-motivated BSc Information Technology (Software Engineering) final-year student with a passion for solving complex business challenges through technology and data. Experienced in software development, process improvement, and cross-functional teamwork. Ready to launch a consulting career with Deloitte's InfinityX Graduate Programme.

EDUCATION
BSc Information Technology (Software Engineering) | Eduvos | 2024 - 2027 (Expected Graduation: November 2026, Top 3 Achiever Year 1)
Learnership in Systems and Design | MICSETA | Completed 2024

TECHNICAL & CONSULTING SKILLS
• Data Analytics (Python, SQL, Excel)
• Software & Application Development (Python, Java, JavaScript, React, Django)
• Business Process Mapping & Improvement
• Risk Analysis & Problem Solving
• System Integration & Automation
• Presentation & Facilitation (Small & Large Groups)
• Project Reporting & Status Tracking
• Client Communication & Stakeholder Engagement

EXPERIENCE
Virtual Java Programming Internship | HexSoftwares (Remote) | Mar 2026 - Apr 2026
• Developed and tested Java applications, collaborating in a distributed team and sharing solutions in weekly syncs.
Web Developer | Freelance | Self-Employed | 2025 - Present
• Designed and delivered web applications for clients, gathering requirements, managing documentation, and deploying solutions that improved business operations.
ICT Youth Development Programme Intern | Sci-Bono Discovery Centre | Mar 2025 - Aug 2025
• Participated in a structured internship focused on software development and Python programming.
IT Support Programme Intern | Quarphix | Jul 2024 - Jan 2025
• Provided technical support, troubleshooting, and user training, developing strong communication and customer service skills.

PROJECTS
Sci-Bono Capstone: Resource-Sharing Platform | Python, Django, PostgreSQL (2025)
• Led requirements analysis, system design, and project documentation for a scalable community resource platform.
Base Blockchain Ecosystem | Python, JavaScript, Next.js (2024)
• Developed a decentralized application focusing on integration, automation, and user experience. Award: 1st Place out of 15+ teams in the Eduvos/Base Blockchain Hackathon.

CERTIFICATIONS
• Johannesburg Lightning Developer Bootcamp (Africa Free Routing & Adopting Bitcoin Cape Town, Feb 2026)
• AI Course for Developers (WeThinkCode_, Mar-Apr 2026)""",
    },
    "visa_vca_consulting": {
        "id": "visa_vca_consulting",
        "label": "Visa Consulting & Analytics (VCA) Intern CV",
        "filename": "Mbesa_Lephoto_Visa_VCA_Intern_CV.pdf",
        "default_company": "Visa",
        "default_role": "Visa Consulting & Analytics (VCA) Intern",
        "default_jd": (
            "Advise banks, fintechs, and major merchants in Sub-Saharan Africa on payments strategy, "
            "card portfolio profitability, risk diagnostics, and data-driven commercial growth. Strong "
            "business case solving, financial analysis, Excel/PowerPoint/Power BI, SQL, and Python."
        ),
        "raw_text": """MBESA LEPHOTO
072 880 8192 | tlephoto14@gmail.com | Midrand, Gauteng (Johannesburg Metropolitan Area) | South African Citizen

PROFESSIONAL SUMMARY
Analytical, client-focused BSc Information Technology (Software Engineering) student (82% average across 19 passed modules, 14 distinctions) available for the VCA Internship in Johannesburg. Combines strong quantitative, financial, and business case solving skills with hands-on experience in Microsoft Excel, PowerPoint, Power BI, SQL (93% Distinction - 100% Exam), Python (91% Distinction), and Machine Learning. Proven ability to gather multi-source data, formulate hypotheses, conduct financial and risk analysis, and translate quantitative findings into executive client recommendations.

EDUCATION
BSc Information Technology (Software Engineering) | Eduvos | 2024 - Expected Graduation: December 2027
• Academic Aggregate: 82% Average across 19 Passed Modules (14 Distinctions | Top 3 Achiever)
Learnership in Systems and Design | MICTSETA | Completed 2024

CONSULTING, ANALYTICS & BUSINESS SKILLS
• Strategy, Consulting & Business Cases: Business Case Analysis, Hypothesis Formulation, Root-Cause Diagnostics, Financial Ratio & Margin Analysis (Net Income, Gross Margin %, Current Ratio), Portfolio & Risk Management, Executive Slides & Client Proposals
• Microsoft Office & BI Tools: Microsoft Excel (Advanced Formulas, Pivot Modeling, Data Validation), Microsoft PowerPoint & Word, Microsoft Power BI (Power Query, Star Schema Modelling, DAX Time Intelligence)
• Data Science, Payments & Programming: SQL (93% Distinction), Python (NumPy, Data Extraction, Automation), Machine Learning Concepts, Payment Transaction Flows, TypeScript & React Dashboards (Recharts)
• Project Management & Stakeholder Alignment: ProjectLibre (Gantt Charts, WBS, Critical Path Analysis), Resource Capacity Trade-offs, Stakeholder Buy-In

BUSINESS CASE, ANALYTICS & PAYMENTS PROJECTS
Enterprise Business Case & Financial Analytics Solution | Microsoft Power BI, Excel, DAX
• Conducted end-to-end financial, operational, and commercial analysis across five datasets (Financials, HR, Sales, Inventory, and Supplier), building a Star Schema and diagnosing Net Income trends (R22.95m to R26.24m to R23.88m), Current Ratio liquidity shifts (1.20 to 1.17), Top 10 accounts (R12.85m net sales), 1.03% regional return friction, supplier scorecards (SUPP_78 at 0.691), and 771 critical stockouts.
Portfolio Management & Resource Allocation Case (ITPMA2-B22) | ProjectLibre, WBS, CPA
• Built a Two-Level WBS, Activity-on-Arrow network model, and ProjectLibre Gantt chart executing Critical Path Analysis for executive resource trade-offs.
Lightning Webstore (Digital Payments & Transaction Analytics) | Python, Flask, REST APIs, SQL
• Engineered a payment processing platform focusing on transaction reliability, checkout user journeys, and SQL data integrity.
VoiceGuard & VeriFace AI (Applied Data Science & Risk Scoring) | Python, PyTorch, NumPy, SQLite
• Applied Exponential Moving Average smoothing, calibrated 0 to 100% risk scoring, and 512-D cosine similarity in Qdrant/SQLite to detect anomalies.

CONSULTING, CLIENT DELIVERY & WORK EXPERIENCE
Freelance Analytics & Software Consultant | Self-Employed | 2025 - 2026
• Partnered directly with business stakeholders to define KPIs and deliver an interactive analytics dashboard under a 2-week MVP deadline to secure client investor funding.
IT Systems & Operations Intern | Quarphix | Jul 2024 - Jan 2025
• Automated bulk account provisioning and access risk revocation via Python and REST APIs, saving 40+ hours per month.""",
    },
    "visa_product_intern": {
        "id": "visa_product_intern",
        "label": "Visa Product Management Intern CV",
        "filename": "Mbesa_Lephoto_Visa_Product_Intern_CV.pdf",
        "default_company": "Visa",
        "default_role": "Product Management Intern",
        "default_jd": (
            "Drive digital payment product ideation, competitor benchmarking, Customer Value Proposition (CVP) "
            "design, concept testing, usability engineering, and cross-functional delivery across product, "
            "design, and engineering teams in Johannesburg."
        ),
        "raw_text": """MBESA LEPHOTO
072 880 8192 | tlephoto14@gmail.com | Midrand, Gauteng (Johannesburg Metropolitan Area) | South African Citizen

PROFESSIONAL SUMMARY
Customer-obsessed, analytical BSc Information Technology (Software Engineering) student (82% average across 19 passed modules, 14 distinctions) with proven experience taking digital products from ideation and concept testing to working MVPs, including shipping a client analytics platform in 2 weeks to secure investor funding and building payment-enabled web software. Combines competitor benchmarking and Customer Value Proposition (CVP) design with Usability Engineering (81% Distinction), Power BI, SQL (93% Distinction), and Python (91% Distinction).

EDUCATION
BSc Information Technology (Software Engineering) | Eduvos | 2024 - Expected Graduation: December 2027 (82% Average, 14 Distinctions, Top 3 Achiever)

PRODUCT, ANALYTICAL & COMMERCIAL SKILLS
• Product Strategy & Ideation: Market Research & Competitor Benchmarking, Customer Value Proposition (CVP) Structuring, Product Ideation & Concept Testing, Local Market Adaptation
• Data, Financial & UX Analysis: Financial Ratio & Margin Analysis, Microsoft Power BI (Power Query, Star Schema, DAX), SQL (93%), Python, Usability Engineering (81%)
• Payments & Digital Platforms: Digital Payment Integration Concepts, Checkout UX Optimization, TypeScript, React (Recharts), FastAPI, AI Product Validation

PRODUCT STRATEGY, ANALYTICS & PAYMENTS PROJECTS
VeriFace AI: Product Ideation, Competitor Benchmarking & Platform Build (face-check) | Next.js, FastAPI, Python
• Conducted competitor benchmarking against FaceCheck.ID, PimEyes, and Lenso.ai, defined a differentiated UX roadmap (Calibrated 0 to 100% Confidence Tiers, global Ctrl+V clipboard workflow, dual-engine candidate discovery), and shipped the full-stack product.
Lightning Webstore (Digital Payments & Checkout Platform) | Python, Flask, REST APIs, SQL
• Built a digital commerce and payment processing platform focusing on seamless checkout flows, transaction integrity, and resilient error handling.
Enterprise Financial & Commercial Insights Solution | Microsoft Power BI, Excel, DAX
• Analyzed Gross Profit Margin % (49.8% to 50.9%), Current Ratio liquidity, regional return friction (1.03%), and Top 10 customer accounts (R12.85m net sales).
Product Delivery Roadmap & Resource Plan (ITPMA2-B22) | ProjectLibre, WBS, CPA, Kanban
• Executed Critical Path Analysis for a 47-day mobile application lifecycle under a Hybrid Agile/Waterfall framework.

PRODUCT DELIVERY & WORK EXPERIENCE
Freelance Product & Software Builder | Self-Employed | 2025 - 2026
• Defined product features, aligned on Customer Value Proposition, and shipped a layout-agnostic React analytics dashboard under a strict 2-week MVP deadline to secure investor funding.
IT Systems & Operations Intern | Quarphix | Jul 2024 - Jan 2025
• Delivered an automated Python and REST API provisioning solution saving 40+ hours per month.""",
    },
    "bluespec_ai_intern": {
        "id": "bluespec_ai_intern",
        "label": "Bluespec AI Developer Intern CV",
        "filename": "Mbesa_Lephoto_Bluespec_AI_Developer_Intern_CV.pdf",
        "default_company": "Bluespec Holdings",
        "default_role": "AI Developer Intern",
        "default_jd": (
            "Build practical enterprise AI applications, LLM validation/retry pipelines, real-time detection "
            "tools, Python workflow automation, Power BI reporting, and cross-departmental integrations across "
            "IT, HR, Operations, and management teams in Sandton."
        ),
        "raw_text": """MBESA LEPHOTO
072 880 8192 | tlephoto14@gmail.com | Midrand, Gauteng (Commutable to Sandton) | South African Citizen

PROFESSIONAL SUMMARY
Innovative and analytical BSc Information Technology (Software Engineering) student (82% average across 19 passed modules, 14 distinctions) seeking the AI Developer Intern (Ref: BSH-334) role at Bluespec Holdings in Sandton. Combines hands-on experience building AI-driven applications, LLM chatbot pipelines (Lowkey AI), and real-time AI detection tools (VoiceGuard, VeriFace AI) with practical enterprise workflow automation (saving 40+ hours per month), Python (91% Distinction), SQL (93% Distinction), and Microsoft Power BI.

COMPETENCIES & TECHNICAL SKILLS
• AI, LLMs & Automation Platforms: ChatGPT, GitHub Copilot, Google Gemini, Large Language Models (LLMs), AI Output Validation & Retry Pipelines, PyTorch, ONNX, InsightFace, Scikit-learn
• Programming & Scripting: Python (FastAPI, Flask, Automation Scripts, Regex, NumPy, Pytest), TypeScript, JavaScript, React, Java (OOP), RESTful APIs
• Data, Reporting & BI Tools: Microsoft Power BI (Power Query ETL, Star Schema Modelling, DAX KPIs), SQL (PostgreSQL, MySQL, SQLite WAL), Recharts Dashboards
• Security, Confidentiality & Documentation: Data Privacy & AI Ethics (86% Distinction), Cryptographic Security (secrets CSPRNG), Parameterized SQL Queries

AI, AUTOMATION & DATA PROJECTS
Lowkey AI: Evaluative Chatbot & LLM Validation Platform | Python, TypeScript, CSS, Git
• Engineered an interactive chatbot evaluation platform and post-processing Python pipeline with regex sanitization layers and length-ratio heuristics to detect hallucinations and trigger graceful automated API retries.
Enterprise BI & Multi-Department Reporting Solution | Microsoft Power BI, Power Query, DAX
• Unified five operational datasets (HR, Financials, Sales, Inventory, Supplier) in Power Query and built a Star Schema with DAX KPIs to analyze HR attrition trends, supplier performance, and inventory risks.
VoiceGuard: Real-Time AI Audio Detection Pipeline (voice-guard) | Python, PyTorch, ONNX, WebSockets
• Built a real-time deepfake voice detector combining RawNet2 neural inference (ONNX) with spectral fallback heuristics, EMA confidence scoring, and a live WebSocket dashboard.
VeriFace AI: Reverse Biometric Discovery Engine (face-check) | Python, FastAPI, Next.js 15, Qdrant, SQLite
• Built a full-stack AI computer vision application pairing RetinaFace/ArcFace embeddings with async FastAPI endpoints and Qdrant/SQLite WAL storage.

PRACTICAL & AUTOMATION EXPERIENCE
IT Systems & Operations Intern | Quarphix | Jul 2024 - Jan 2025
• Engineered a secure Python identity lifecycle automation script (secrets CSPRNG) and REST APIs for bulk provisioning and session revocation, saving 40+ hours/month.
ICT Youth Development Programme Intern | Sci-Bono Discovery Centre | Mar 2025 - Aug 2025
• Developed Python workflow automation scripts eliminating manual data entry bottlenecks.
Freelance Software & Dashboard Developer | Self-Employed | 2025 - 2026
• Architected a layout-agnostic React and TypeScript analytics dashboard under a 2-week MVP deadline.""",
    },
    "cape_union_mart_bi": {
        "id": "cape_union_mart_bi",
        "label": "Cape Union Mart BI Intern CV",
        "filename": "Mbesa_Lephoto_Cape_Union_Mart_BI_Intern_CV.pdf",
        "default_company": "Cape Union Mart",
        "default_role": "Business Intelligence (BI) Intern",
        "default_jd": (
            "Support retail, merchandise, and e-commerce analytics using SQL, Oracle Analytics Cloud / Power BI, "
            "dimensional data modeling (Star Schema), daily data quality checks, UAT testing, user support guides, "
            "and Python data cleaning scripts."
        ),
        "raw_text": """MBESA LEPHOTO
072 880 8192 | tlephoto14@gmail.com | Cape Town, Western Cape | South African Citizen

PROFESSIONAL SUMMARY
Curious, detail-oriented BSc Information Technology (Software Engineering) student (82% academic average, Top 3 Achiever) eager to turn retail, merchandise, and e-commerce data into actionable insights as a BI Intern at Cape Union Mart International. Brings a strong foundation in SQL, Python, Microsoft Excel, and relational data modelling, paired with practical projects in Power BI dashboards, automated data cleaning, and anomaly validation. Ready to learn Oracle Retail, Retail Insights (RI), and Oracle Analytics Cloud (OAC).

COMPETENCIES & BI SKILLS
• BI, Reporting & Analytics Tools: Microsoft Power BI Desktop (Power Query M Language, DAX Measures, Star Schema Modelling, KPI Scorecards), Interactive Web Dashboards (Recharts, MetricPoint[]), Microsoft Excel, UAT Testing
• Databases & Data Warehousing: SQL (PostgreSQL, MySQL, SQLite), Dimensional Data Modelling (Fact & Dimension Tables, CALENDAR, 1:* Relationships), Normalization, DAO Pattern
• Data Preparation & Python: Python (Data Cleaning, Extraction, Validation Pipelines, Pytest), Regex Sanitization, Anomaly Flagging, NumPy

DATA, ANALYTICS & RETAIL-ALIGNED PROJECTS
Enterprise BI & Supply Chain Dashboard Solution | Microsoft Power BI, Power Query, DAX, Star Schema
• Engineered a multi-page Power BI solution unifying five operational datasets (Financials, HR, Sales, Inventory, Supplier), building a Star Schema (CALENDAR, DimProduct, DimSupplier, DimCustomer) and complex DAX measures for Gross Profit Margin, Net Sales after Returns, and Critical Stock Counts below Reorder Level.
Analytics Dashboard Platform (Freelance Project) | TypeScript, React, Recharts
• Built a modular, layout-agnostic analytics dashboard under a 2-week deadline with strict MetricPoint[] interfaces.
Lightning Webstore (E-Commerce & Transactional Data) | Python, Flask, REST APIs, SQL
• Developed an e-commerce webstore backend handling product catalogues, order workflows, and transactional SQL validation.
Lowkey AI: Data Cleaning & Anomaly Validation Pipeline | Python, Regex
• Engineered a Python pipeline to clean, validate, and flag malformed or truncated outputs.
VeriFace AI & VoiceGuard | Python, SQLite (WAL), Qdrant, FastAPI
• Built multi-source data ingestion pipelines with pytest validation suites.

PRACTICAL & SUPPORT EXPERIENCE
IT Systems & Operations Intern | Quarphix | Jul 2024 - Jan 2025
• Performed daily infrastructure monitoring checks, logged and escalated support requests, prepared user guides, and saved 40+ hours/month via Python REST API automation.
ICT Youth Development Intern | Sci-Bono Discovery Centre | Mar 2025 - Aug 2025
• Automated manual record entry via Python scripts.""",
    },
    "amazon_dco_tech": {
        "id": "amazon_dco_tech",
        "label": "Amazon DCO Tech Intern CV",
        "filename": "Mbesa_Lephoto_Amazon_DCO_Tech_Intern_CV.pdf",
        "default_company": "Amazon",
        "default_role": "Data Center Operations (DCO) Tech Intern",
        "default_jd": (
            "Maintain mission-critical server and network infrastructure inside AWS Data Centers in Cape Town. "
            "Diagnose server hardware faults (CPU, RAM, PSU, SSD/NVMe), troubleshoot Linux OS and local network "
            "links (TCP/IP, DNS, DHCP, subnetting), execute trouble tickets within SLAs, and uphold safety & Amazon LPs."
        ),
        "raw_text": """MBESA LEPHOTO
072 880 8192 | tlephoto14@gmail.com | Cape Town, Western Cape | South African Citizen

PROFESSIONAL SUMMARY
Hands-on, safety-conscious Information Technology student (82% academic average, Top 3 Achiever) with a completed MICTSETA Learnership in Systems and Design and practical experience in enterprise IT infrastructure support, hardware and network diagnostics, Linux environments, and ticket-driven SLA execution. Driven by Amazon's principles of Ownership, Bias for Action, and Insist on the Highest Standards, and eager to maintain mission-critical server and network infrastructure as a Data Center Operations (DCO) Tech Intern at Amazon Data Services South Africa.

EDUCATION & ACCREDITED TRAINING
BSc Information Technology (Software Engineering) | Eduvos | 2024 - Present
• Relevant Passed Modules: Computer Network and Security (96%), Computer Network Technologies (96%), Linux-based Operating Systems (92%), Network Security (91%), Cloud Based Technologies (71%), Database Systems (93%)
Learnership in Systems and Design | MICTSETA | Completed 2024

COMPETENCIES & TECHNICAL SKILLS
• Hardware & Data Center Fundamentals: Server & Workstation Component Architecture (CPUs, GPUs, RAM, Motherboards, SSDs/HDDs), Hardware Diagnostics, Component Replacement, Physical Troubleshooting
• Linux & Networking: Linux/Unix CLI (File Systems, Process Monitoring, System Logs, Diagnostics), Windows OS, TCP/IP, DNS, DHCP, Subnetting, Local Network Link Troubleshooting
• Operations & SLA Execution: Trouble Ticketing Workflows, SLA Prioritization, Technical Runbooks & Operational Documentation, Incident Escalation
• Scripting, Cloud & Security: Python Scripting & Automation, Bash Basics, REST APIs, Docker & Containerization, AWS

WORK & OPERATIONS EXPERIENCE
IT Systems & Operations Intern | Quarphix | Jul 2024 - Jan 2025
• Supported daily enterprise IT infrastructure operations by monitoring system health, diagnosing hardware and local network faults, resolving trouble tickets within SLAs, authoring troubleshooting runbooks, and automating account provisioning (saving 40+ hours/month).
ICT Youth Development Programme Intern | Sci-Bono Discovery Centre | Mar 2025 - Aug 2025
• Supported digital systems, workstation setups, and technical lab equipment, troubleshooting daily hardware and software issues.

SYSTEMS & INFRASTRUCTURE PROJECTS
VoiceGuard: Real-Time CPU Inference & Device CLI Tool (voice-guard) | Python, ONNX, CLI
• Engineered a command-line diagnostic and real-time audio monitoring system supporting hardware device enumeration (--device), CPU-optimized ONNX runtime inference, and configurable alert thresholds.
VeriFace AI: Containerized Compute Pipeline (face-check) | Docker Compose, Python, PowerShell
• Configured multi-service containerized deployment (docker-compose.yml) and scripted server lifecycle management (start-veriface.ps1).
Lightning Webstore (Distributed Backend & Networking) | Python, Flask, REST APIs, SQL
• Deployed and tested fault-tolerant backend services interacting with distributed network nodes.""",
    },
}
