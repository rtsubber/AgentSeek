#!/usr/bin/env python3
"""Bulk add agents to AgentSeek directory to fill out thin categories."""

import sqlite3
import json
import time

DB_PATH = "/home/ron/.openclaw/workspace/agent-registry/app/agent_registry.db"

# New agents to add - focusing on thin categories
# Format: (id, name, description, endpoint_url, website_url, logo_url, category, tags, auth_method, pricing_model, pricing_details, trust_score)

NEW_AGENTS = [
    # === HEALTHCARE (1→5) ===
    ("ext_aida_health_001", "Aida Health", "AI-powered symptom checker and health information assistant that provides preliminary assessments and connects patients with healthcare providers.", "https://api.aidahealth.com", "https://www.aidahealth.com", "https://www.google.com/s2/favicons?sz=64&domain=aidahealth.com", "healthcare", "symptoms,health,triage,patient_assessment,telemedicine", "api_key", "freemium", '{"free": "Basic symptom check", "paid": "$29/mo for clinical decision support"}', 76.0),
    
    ("ext_zocdoc_001", "Zocdoc AI", "AI-powered doctor search and appointment scheduling platform. Matches patients with providers by specialty, insurance, and availability.", "https://api.zocdoc.com", "https://www.zocdoc.com", "https://www.google.com/s2/favicons?sz=64&domain=zocdoc.com", "healthcare", "appointments,doctor_search,insurance,scheduling,healthcare", "api_key", "free", '{"free": "Patient-facing search is free", "paid": "Provider listings from $300/mo"}', 82.0),
    
    ("ext_talkiatry_001", "Talkiatry AI", "AI-assisted psychiatry platform that matches patients with psychiatrists for virtual mental health appointments, with AI-powered intake and screening.", "https://api.talkiatry.com", "https://www.talkiatry.com", "https://www.google.com/s2/favicons?sz=64&domain=talkiatry.com", "healthcare", "mental_health,psychiatry,virtual_care,screening,matching", "api_key", "free", '{"free": "Patient matching is free", "paid": "Insurance-based psychiatric care"}', 78.0),
    
    ("ext_health_gorilla_001", "Health Gorilla", "AI-powered clinical data exchange platform that aggregates and normalizes health data from EHRs, labs, and pharmacies for unified patient records.", "https://api.healthgorilla.com", "https://www.healthgorilla.com", "https://www.google.com/s2/favicons?sz=64&domain=healthgorilla.com", "healthcare", "ehr,data_exchange,clinical_data,FHIR,interoperability", "api_key", "enterprise", '{"paid": "Custom enterprise pricing"}', 80.0),

    # === LEGAL (2→6) ===
    ("ext_casetext_001", "Casetext by Thomson Reuters", "AI legal research assistant powered by CoCounsel. Searches case law, statutes, and regulations with AI-generated summaries and analysis.", "https://api.casetext.com", "https://casetext.com", "https://www.google.com/s2/favicons?sz=64&domain=casetext.com", "legal", "legal_research,case_law,statutes,analysis,summarization", "api_key", "paid", '{"paid": "CoCounsel starts at $200/mo per seat"}', 85.0),
    
    ("ext_legalrobot_001", "LegalRobot", "AI contract analysis and legal document review agent. Automatically identifies risks, ambiguities, and compliance issues in legal documents.", "https://api.legalrobot.com", "https://www.legalrobot.com", "https://www.google.com/s2/favicons?sz=64&domain=legalrobot.com", "legal", "contract_analysis,compliance,risk_detection,document_review", "api_key", "freemium", '{"free": "3 documents/mo", "paid": "$29/mo for unlimited analysis"}', 73.0),
    
    ("ext_spellbook_001", "Spellbook", "AI contract drafting and review assistant for lawyers. Suggests clauses, flags risks, and accelerates contract workflows using GPT-4.", "https://api.spellbook.com", "https://www.spellbook.legal", "https://www.google.com/s2/favicons?sz=64&domain=spellbook.legal", "legal", "contract_drafting,clause_suggestion,risk_flagging,litigation", "api_key", "paid", '{"paid": "Enterprise pricing, per-seat licensing"}', 81.0),
    
    ("ext_eve_legal_001", "Eve by Cleo", "AI legal assistant that helps personal injury firms with case intake, document analysis, demand letter drafting, and timeline construction.", "https://api.eve.legal", "https://www.eve.legal", "https://www.google.com/s2/favicons?sz=64&domain=eve.legal", "legal", "personal_injury,case_intake,demand_letters,document_analysis", "api_key", "enterprise", '{"paid": "Custom enterprise pricing"}', 74.0),

    # === REAL ESTATE (1→4) ===
    ("ext_redfin_001", "Redfin AI", "AI-powered real estate search and valuation platform with predictive pricing, neighborhood insights, and automated home touring.", "https://api.redfin.com", "https://www.redfin.com", "https://www.google.com/s2/favicons?sz=64&domain=redfin.com", "real_estate", "property_search,valuation,neighborhood_insights,touring", "api_key", "free", '{"free": "Search and basic estimates", "paid": "API access from $500/mo"}', 86.0),
    
    ("ext_zillow_001", "Zillow AI", "AI-driven real estate marketplace with Zestimate home valuations, rental estimates, and neighborhood analytics for buyers, sellers, and renters.", "https://api.zillow.com", "https://www.zillow.com", "https://www.google.com/s2/favicons?sz=64&domain=zillow.com", "real_estate", "home_valuation,rental_estimates,marketplace,neighborhood_data", "api_key", "freemium", '{"free": "Basic property data", "paid": "API from $200/mo"}', 88.0),
    
    ("ext_housecanary_001", "HouseCanary", "AI-powered property analytics and valuation platform providing predictive home values, investment risk scores, and market forecasts for real estate professionals.", "https://api.housecanary.com", "https://www.housecanary.com", "https://www.google.com/s2/favicons?sz=64&domain=housecanary.com", "real_estate", "analytics,valuation,risk_scoring,market_forecasts,investing", "api_key", "paid", '{"paid": "API plans from $50/mo"}', 79.0),

    # === SECURITY (1→4) ===
    ("ext_wiz_001", "Wiz AI Security", "AI-powered cloud security platform that maps attack paths, identifies toxic combinations, and provides continuous risk assessment for cloud infrastructure.", "https://api.wiz.io", "https://www.wiz.io", "https://www.google.com/s2/favicons?sz=64&domain=wiz.io", "security", "cloud_security,attack_path,risk_assessment,infrastructure,compliance", "api_key", "enterprise", '{"paid": "Custom enterprise pricing"}', 87.0),
    
    ("ext_snyk_001", "Snyk", "AI-powered developer security platform that finds and fixes vulnerabilities in code, dependencies, containers, and infrastructure as code.", "https://api.snyk.io", "https://snyk.io", "https://www.google.com/s2/favicons?sz=64&domain=snyk.io", "security", "vulnerability_scanning,code_security,dependency_check,container_security", "api_key", "freemium", '{"free": "200 tests/mo for open source", "paid": "Pro from $98/mo"}', 86.0),
    
    ("ext_abnormal_001", "Abnormal Security", "AI-powered email security platform that detects and prevents business email compromise, phishing, and account takeover using behavioral analysis.", "https://api.abnormalsecurity.com", "https://abnormalsecurity.com", "https://www.google.com/s2/favicons?sz=64&domain=abnormalsecurity.com", "security", "email_security,phishing,BEC_detection,behavioral_analysis", "api_key", "enterprise", '{"paid": "Custom enterprise pricing"}', 83.0),

    # === EDUCATION (1→4) ===
    ("ext_duolingo_001", "Duolingo AI", "AI-powered language learning platform with adaptive lessons, speech recognition, and personalized learning paths for 40+ languages.", "https://api.duolingo.com", "https://www.duolingo.com", "https://www.google.com/s2/favicons?sz=64&domain=duolingo.com", "education", "language_learning,adaptive,personalized,speech_recognition,gamification", "api_key", "freemium", '{"free": "Full language courses", "paid": "Super Duolingo from $6.99/mo"}', 88.0),
    
    ("ext_coursera_001", "Coursera AI", "AI-powered online education platform offering courses, certifications, and degrees from top universities with personalized learning recommendations.", "https://api.coursera.org", "https://www.coursera.org", "https://www.google.com/s2/favicons?sz=64&domain=coursera.org", "education", "online_courses,certifications,universities,skills,recommendations", "api_key", "freemium", '{"free": "Audit most courses free", "paid": "Certificates from $49, degrees from $9,000"}', 85.0),
    
    ("ext_quillbot_001", "QuillBot AI", "AI writing and paraphrasing assistant for students and professionals. Offers grammar checking, citation generation, and text summarization.", "https://api.quillbot.com", "https://quillbot.com", "https://www.google.com/s2/favicons?sz=64&domain=quillbot.com", "education", "paraphrasing,grammar,writing,summarization,citations", "api_key", "freemium", '{"free": "125 words/paraphrase", "paid": "Premium from $9.95/mo"}', 77.0),

    # === HR (1→4) ===
    ("ext_hired_001", "Hired AI", "AI-powered talent marketplace that matches tech talent with companies using skill-based assessments and salary transparency.", "https://api.hired.com", "https://www.hired.com", "https://www.google.com/s2/favicons?sz=64&domain=hired.com", "hr", "talent_marketplace,matching,salary_data,tech_recruiting", "api_key", "freemium", '{"free": "Job seekers free", "paid": "Employers from $6,000/yr"}', 75.0),
    
    ("ext_greenhouse_001", "Greenhouse AI", "AI-powered hiring platform with structured interviews, bias reduction, and data-driven candidate evaluation for fair and effective recruiting.", "https://api.greenhouse.io", "https://www.greenhouse.io", "https://www.google.com/s2/favicons?sz=64&domain=greenhouse.io", "hr", "hiring,structured_interviews,bias_reduction,candidate_evaluation", "api_key", "enterprise", '{"paid": "Custom enterprise pricing, from $6,000/yr"}', 84.0),
    
    ("ext_pymetrics_001", "Pymetrics", "AI-driven talent matching platform using neuroscience-based games and algorithms to match candidates with careers while reducing hiring bias.", "https://api.pymetrics.ai", "https://www.pymetrics.ai", "https://www.google.com/s2/favicons?sz=64&domain=pymetrics.ai", "hr", "talent_matching,neuroscience,bias_reduction,career_assessment,gamification", "api_key", "enterprise", '{"paid": "Enterprise pricing"}', 72.0),

    # === ANALYTICS (1→4) ===
    ("ext_tableau_001", "Tableau AI", "AI-powered data visualization and business intelligence platform with natural language queries, automated insights, and interactive dashboards.", "https://api.tableau.com", "https://www.tableau.com", "https://www.google.com/s2/favicons?sz=64&domain=tableau.com", "analytics", "data_visualization,business_intelligence,dashboards,NLQ,insights", "api_key", "paid", '{"paid": "Creator from $70/user/mo"}', 87.0),
    
    ("ext_looker_001", "Looker AI", "AI-powered data analytics and business intelligence platform by Google Cloud. Provides LookML modeling, embedded analytics, and AI-generated insights.", "https://api.looker.com", "https://www.looker.com", "https://www.google.com/s2/favicons?sz=64&domain=looker.com", "analytics", "business_intelligence,data_modeling,embedded_analytics,AI_insights,LookML", "api_key", "enterprise", '{"paid": "Custom enterprise pricing"}', 83.0),
    
    ("ext_mode_001", "Mode AI", "AI-powered analytics platform combining SQL, Python, and visual analysis with collaborative reporting and real-time data exploration.", "https://api.modeanalytics.com", "https://mode.com", "https://www.google.com/s2/favicons?sz=64&domain=mode.com", "analytics", "sql,python,visual_analysis,collaborative_reporting,data_exploration", "api_key", "freemium", '{"free": "Public reports free", "paid": "Pro from $5,000/yr"}', 76.0),

    # === CAREER (1→4) ===
    ("ext_indeed_001", "Indeed AI", "AI-powered job search platform with smart matching, salary comparison, resume screening, and personalized job recommendations.", "https://api.indeed.com", "https://www.indeed.com", "https://www.google.com/s2/favicons?sz=64&domain=indeed.com", "career", "job_search,smart_matching,salary_comparison,resume_screening", "api_key", "freemium", '{"free": "Job seekers free", "paid": "Employer sponsored listings"}', 85.0),
    
    ("ext_lever_001", "Lever AI", "AI-powered hiring platform with candidate relationship management, automated outreach, and pipeline analytics for modern recruiting teams.", "https://api.lever.co", "https://www.lever.co", "https://www.google.com/s2/favicons?sz=64&domain=lever.co", "career", "hiring,CRM,outreach_automation,pipeline_analytics,recruiting", "api_key", "enterprise", '{"paid": "From $3,600/yr"}', 79.0),
    
    ("ext_pathrise_001", "Pathrise", "AI-enhanced career accelerator that provides job search coaching, resume optimization, interview prep, and salary negotiation using data-driven matching.", "https://api.pathrise.com", "https://www.pathrise.com", "https://www.google.com/s2/favicons?sz=64&domain=pathrise.com", "career", "career_coaching,resume_optimization,interview_prep,salary_negotiation", "api_key", "paid", '{"paid": "Income share agreement or $3,000 upfront"}', 71.0),

    # === VERIFICATION (1→3) ===
    ("ext_trulioo_001", "Trulioo", "AI-powered identity verification and business verification platform with global coverage across 190+ countries for KYC, AML, and compliance.", "https://api.trulioo.com", "https://www.trulioo.com", "https://www.google.com/s2/favicons?sz=64&domain=trulioo.com", "verification", "identity_verification,KYC,AML,compliance,business_verification", "api_key", "paid", '{"paid": "Per-verification pricing from $0.50/check"}', 84.0),
    
    ("ext_onfido_001", "Onfido by Entrust", "AI-powered identity verification using document and biometric checks. Verifies IDs, passports, and selfies with fraud detection for onboarding.", "https://api.onfido.com", "https://onfido.com", "https://www.google.com/s2/favicons?sz=64&domain=onfido.com", "verification", "identity_verification,document_check,biometric,fraud_detection,onboarding", "api_key", "paid", '{"paid": "From $1.50/verification"}', 81.0),

    # === TOOLS (1→4) ===
    ("ext_postman_001", "Postman AI", "AI-powered API development platform with intelligent request generation, automated testing, and API documentation using AI assistants.", "https://api.postman.com", "https://www.postman.com", "https://www.google.com/s2/favicons?sz=64&domain=postman.com", "tools", "api_development,testing,documentation,AI_assistant,workflows", "api_key", "freemium", '{"free": "Basic plan free", "paid": "Pro from $14/user/mo"}', 86.0),
    
    ("ext_vercel_001", "Vercel AI", "AI-powered deployment platform with v0 for generative UI, AI SDK for building AI apps, and instant edge deployments for Next.js.", "https://api.vercel.com", "https://vercel.com", "https://www.google.com/s2/favicons?sz=64&domain=vercel.com", "tools", "deployment,generative_ui,AI_SDK,edge_computing,Next.js", "api_key", "freemium", '{"free": "Hobby plan free", "paid": "Pro from $20/user/mo"}', 89.0),
    
    ("ext_supabase_001", "Supabase", "AI-powered open-source backend platform with PostgreSQL, real-time subscriptions, edge functions, and built-in vector/AI support for app development.", "https://api.supabase.com", "https://supabase.com", "https://www.google.com/s2/favicons?sz=64&domain=supabase.com", "tools", "backend,database,realtime,edge_functions,vector,AI_embeddings", "api_key", "freemium", '{"free": "2 projects free", "paid": "Pro from $25/mo"}', 85.0),

    # === CUSTOMER SUPPORT (2→6) ===
    ("ext_freshdesk_001", "Freshdesk AI", "AI-powered customer support platform with automated ticket routing, AI chatbots, sentiment analysis, and knowledge base management.", "https://api.freshdesk.com", "https://freshdesk.com", "https://www.google.com/s2/favicons?sz=64&domain=freshdesk.com", "customer_support", "ticket_routing,chatbot,sentiment_analysis,knowledge_base,automation", "api_key", "freemium", '{"free": "Up to 10 agents free", "paid": "Growth from $15/agent/mo"}', 82.0),
    
    ("ext_tidio_001", "Tidio AI", "AI live chat and chatbot platform for small businesses. Combines live chat, AI chatbot, and helpdesk with ecommerce integrations.", "https://api.tidio.com", "https://www.tidio.com", "https://www.google.com/s2/favicons?sz=64&domain=tidio.com", "customer_support", "live_chat,chatbot,helpdesk,ecommerce,small_business", "api_key", "freemium", '{"free": "Up to 50 conversations/mo", "paid": "Communicator from $29/mo"}', 74.0),
    
    ("ext_gorgias_001", "Gorgias AI", "AI-powered ecommerce helpdesk that automates customer support with AI-generated responses, ticket categorization, and Shopify integration.", "https://api.gorgias.com", "https://www.gorgias.com", "https://www.google.com/s2/favicons?sz=64&domain=gorgias.com", "customer_support", "ecommerce,helpdesk,automated_responses,Shopify,ticket_categorization", "api_key", "paid", '{"paid": "From $60/mo for 350 tickets"}', 80.0),
    
    ("ext_kustomer_001", "Kustomer AI", "AI-first CRM and customer service platform with conversational AI, automated workflows, and omnichannel support for enterprise.", "https://api.kustomer.com", "https://www.kustomer.com", "https://www.google.com/s2/favicons?sz=64&domain=kustomer.com", "customer_support", "CRM,conversational_AI,omnichannel,workflows,enterprise", "api_key", "enterprise", '{"paid": "Custom enterprise pricing"}', 77.0),

    # === AUTOMATION (2→6) ===
    ("ext_n8n_001", "n8n", "Open-source workflow automation platform with AI agent nodes, 400+ integrations, and self-hosted or cloud deployment for building AI-powered automations.", "https://api.n8n.io", "https://n8n.io", "https://www.google.com/s2/favicons?sz=64&domain=n8n.io", "automation", "workflow,AI_agents,integrations,self_hosted,low_code", "api_key", "freemium", '{"free": "Self-hosted free, cloud free tier", "paid": "Cloud Starter from $20/mo"}', 84.0),
    
    ("ext_activepieces_001", "Activepieces", "Open-source AI automation platform with 200+ integrations, AI-powered actions, and self-hosted or cloud deployment for workflow automation.", "https://api.activepieces.com", "https://www.activepieces.com", "https://www.google.com/s2/favicons?sz=64&domain=activepieces.com", "automation", "workflow,integrations,AI_actions,self_hosted,no_code", "api_key", "freemium", '{"free": "Cloud free tier or self-hosted", "paid": "Pro from $50/mo"}', 73.0),
    
    ("ext_bardeen_001", "Bardeen AI", "AI-powered workflow automation that records actions, suggests automations, and executes them across web apps using natural language commands.", "https://api.bardeen.ai", "https://www.bardeen.ai", "https://www.google.com/s2/favicons?sz=64&domain=bardeen.ai", "automation", "workflow,natural_language,web_automation,recording,suggestions", "api_key", "freemium", '{"free": "Basic automations free", "paid": "Pro from $15/mo"}', 78.0),
    
    ("ext_rewind_001", "Rewind AI", "AI-powered productivity assistant that records screen activity and makes everything you've seen searchable. Privacy-first with local processing.", "https://api.rewind.ai", "https://www.rewind.ai", "https://www.google.com/s2/favicons?sz=64&domain=rewind.ai", "automation", "screen_recording,search,productivity,privacy,local_processing", "api_key", "freemium", '{"free": "Basic recording free", "paid": "Pro from $19/mo"}', 76.0),

    # === DATA (2→5) ===
    ("ext_scrapeless_001", "Scrapeless", "AI-powered web scraping platform with anti-detection, CAPTCHA solving, and data extraction APIs for structured data collection.", "https://api.scrapeless.com", "https://www.scrapeless.com", "https://www.google.com/s2/favicons?sz=64&domain=scrapeless.com", "data", "web_scraping,anti_detection,CAPTCHA,data_extraction,API", "api_key", "freemium", '{"free": "1,000 credits/mo", "paid": "Starter from $49/mo"}', 72.0),
    
    ("ext_bright_data_001", "Bright Data", "AI-powered data collection platform with residential proxies, web scraping APIs, and dataset marketplace for large-scale web data extraction.", "https://api.brightdata.com", "https://brightdata.com", "https://www.google.com/s2/favicons?sz=64&domain=brightdata.com", "data", "proxy,web_scraping,datasets,data_collection,residential_IPs", "api_key", "paid", '{"paid": "Pay-as-you-go or plans from $500/mo"}', 83.0),
    
    ("ext_oxylabs_001", "Oxylabs AI", "AI-powered proxy and web data extraction platform with residential and datacenter proxies, SERP API, and e-commerce scraping tools.", "https://api.oxylabs.io", "https://oxylabs.io", "https://www.google.com/s2/favicons?sz=64&domain=oxylabs.io", "data", "proxy,SERP,web_scraping,ecommerce,data_collection", "api_key", "paid", '{"paid": "Pay-as-you-go from $75/mo"}', 80.0),

    # === MARKETING (2→5) ===
    ("ext_jasper_001", "Jasper AI", "AI content creation and marketing platform with brand voice, campaign workflows, and multi-channel content generation for marketing teams.", "https://api.jasper.ai", "https://www.jasper.ai", "https://www.google.com/s2/favicons?sz=64&domain=jasper.ai", "marketing", "content_creation,brand_voice,campaigns,multi_channel,marketing", "api_key", "paid", '{"paid": "Creator from $49/mo, Pro from $69/mo"}', 83.0),
    
    ("ext_mailchimp_001", "Mailchimp AI", "AI-powered email marketing and automation platform with predictive segmentation, content optimization, and customer journey mapping.", "https://api.mailchimp.com", "https://mailchimp.com", "https://www.google.com/s2/favicons?sz=64&domain=mailchimp.com", "marketing", "email_marketing,automation,segmentation,customer_journey,AI_content", "api_key", "freemium", '{"free": "Up to 500 contacts", "paid": "Essentials from $13/mo"}', 85.0),
    
    ("ext_hubspot_001", "HubSpot AI", "AI-powered CRM and marketing platform with content assistant, chatbot builder, predictive lead scoring, and automated workflows.", "https://api.hubspot.com", "https://www.hubspot.com", "https://www.google.com/s2/favicons?sz=64&domain=hubspot.com", "marketing", "CRM,content_assistant,lead_scoring,chatbot,workflows", "api_key", "freemium", '{"free": "Free CRM and tools", "paid": "Starter from $20/mo"}', 87.0),

    # === DEVELOPER TOOLS (8→12) ===
    ("ext_v0_001", "Vercel v0", "AI-powered generative UI tool that creates React components from text prompts using shadcn/ui and Tailwind CSS. Build production-ready UIs instantly.", "https://api.vercel.com/v0", "https://v0.dev", "https://www.google.com/s2/favicons?sz=64&domain=v0.dev", "developer_tools", "generative_UI,React,Next.js,shadcn,Tailwind_CSS", "api_key", "freemium", '{"free": "10 generations/mo", "paid": "Premium from $20/mo"}', 88.0),
    
    ("ext_bolt_001", "Bolt.new by StackBlitz", "AI-powered full-stack web development environment that generates, runs, and deploys complete web applications from natural language prompts in the browser.", "https://bolt.new", "https://bolt.new", "https://www.google.com/s2/favicons?sz=64&domain=bolt.new", "developer_tools", "full_stack,web_development,deployment,NL_prompts,browser_IDE", "api_key", "freemium", '{"free": "Basic usage free", "paid": "Pro from $20/mo"}', 82.0),
    
    ("ext_lovable_001", "Lovable (ex-GPT Engineer)", "AI-powered app builder that generates full-stack web applications from natural language descriptions with real-time preview and deployment.", "https://lovable.dev", "https://lovable.dev", "https://www.google.com/s2/favicons?sz=64&domain=lovable.dev", "developer_tools", "app_builder,full_stack,NL_prompts,deployment,React", "api_key", "freemium", '{"free": "5 projects free", "paid": "Pro from $20/mo"}', 79.0),
    
    ("ext_devin_001", "Devin by Cognition", "Autonomous AI software engineer that can plan, code, debug, and deploy software end-to-end. Handles multi-step engineering tasks independently.", "https://api.cognition.ai", "https://www.cognition.ai", "https://www.google.com/s2/favicons?sz=64&domain=cognition.ai", "developer_tools", "autonomous_engineering,coding,debugging,deployment,multi_step", "api_key", "paid", '{"paid": "Access from $500/mo"}', 80.0),

    # === COMMUNICATION (7→10) ===
    ("ext_openai_001", "OpenAI Realtime API", "AI voice and text communication platform with real-time speech-to-speech, function calling, and multimodal conversation capabilities for building voice agents.", "https://api.openai.com", "https://platform.openai.com", "https://www.google.com/s2/favicons?sz=64&domain=openai.com", "communication", "voice,realtime,speech_to_speech,function_calling,multimodal", "api_key", "paid", '{"paid": "Pay-per-use: text $3/M tokens, audio $0.06/min"}', 93.0),
    
    ("ext_twilio_001", "Twilio AI", "AI-powered communication platform with voice, messaging, and email APIs. Adds intelligent call routing, transcription, and conversational AI to any application.", "https://api.twilio.com", "https://www.twilio.com", "https://www.google.com/s2/favicons?sz=64&domain=twilio.com", "communication", "voice,SMS,email,call_routing,transcription", "api_key", "paid", '{"paid": "Pay-per-use: SMS from $0.0079/msg"}', 90.0),
    
    ("ext_livekit_001", "LiveKit", "Open-source real-time audio/video infrastructure for AI agents. WebRTC-based with agent frameworks, SIP integration, and multi-participant rooms.", "https://api.livekit.io", "https://livekit.io", "https://www.google.com/s2/favicons?sz=64&domain=livekit.io", "communication", "realtime,audio,video,WebRTC,SIP,agent_framework", "api_key", "freemium", '{"free": "Self-hosted free, cloud free tier", "paid": "Cloud from $50/mo"}', 81.0),

    # === PRODUCTIVITY (3→6) ===
    ("ext_notion_001", "Notion AI", "AI-powered workspace with writing assistant, knowledge base, project management, and database automation for teams and individuals.", "https://api.notion.com", "https://www.notion.so", "https://www.google.com/s2/favicons?sz=64&domain=notion.so", "productivity", "workspace,writing_assistant,knowledge_base,project_management,databases", "api_key", "freemium", '{"free": "Basic plan free", "paid": "Plus from $10/user/mo, AI $10/user/mo"}', 88.0),
    
    ("ext_otter_001", "Otter.ai", "AI-powered meeting transcription and note-taking assistant that provides real-time transcription, summaries, action items, and meeting chat.", "https://api.otter.ai", "https://otter.ai", "https://www.google.com/s2/favicons?sz=64&domain=otter.ai", "productivity", "transcription,meeting_notes,summaries,action_items,collaboration", "api_key", "freemium", '{"free": "300 min/mo", "paid": "Pro from $16.99/mo"}', 80.0),
    
    ("ext_gamma_001", "Gamma AI", "AI-powered presentation and document creator that generates polished slides, reports, and webpages from text prompts with smart formatting and design.", "https://api.gamma.app", "https://gamma.app", "https://www.google.com/s2/favicons?sz=64&domain=gamma.app", "productivity", "presentations,documents,slides,NL_prompts,design", "api_key", "freemium", '{"free": "400 AI credits free", "paid": "Plus from $10/mo"}', 77.0),

    # === SEARCH (3→5) ===
    ("ext_google_gemini_001", "Google Gemini", "AI-powered search and reasoning engine with multimodal capabilities, real-time information access, and code generation across text, image, and video.", "https://generativelanguage.googleapis.com", "https://gemini.google.com", "https://www.google.com/s2/favicons?sz=64&domain=gemini.google.com", "search", "multimodal,reasoning,real_time,code_generation,grounded_search", "api_key", "freemium", '{"free": "Gemini Flash free tier", "paid": "API pay-per-use, Advanced from $20/mo"}', 92.0),
    
    ("ext_brave_search_001", "Brave Search API", "Privacy-focused search API with AI-powered summarization, real-time results, and independent web index. Built-in summarizer for instant answers.", "https://api.search.brave.com", "https://brave.com/search/api", "https://www.google.com/s2/favicons?sz=64&domain=brave.com", "search", "privacy,real_time,summarization,independent_index,API", "api_key", "freemium", '{"free": "2,000 queries/mo", "paid": "Base from $3/1000 queries"}', 79.0),
]

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    added = 0
    skipped = 0
    now = time.time()
    
    for agent in NEW_AGENTS:
        (agent_id, name, description, endpoint_url, website_url, logo_url, 
         category, tags, auth_method, pricing_model, pricing_details, trust_score) = agent
        
        # Check if already exists
        cursor.execute("SELECT id FROM agents WHERE id = ?", (agent_id,))
        if cursor.fetchone():
            print(f"  SKIP {name} (already exists)")
            skipped += 1
            continue
        
        # Build manifest
        manifest = json.dumps({
            "name": name,
            "description": description[:200],
            "version": "1.0",
            "capabilities": [t.strip() for t in tags.split(",")],
            "endpoint": endpoint_url,
            "auth_method": auth_method,
            "pricing": json.loads(pricing_details),
            "category": category
        })
        
        cursor.execute("""
            INSERT INTO agents (
                id, name, description, endpoint_url, owner_email, owner_name,
                website_url, logo_url, manifest_json, verified, trust_score,
                total_calls, success_rate, monthly_calls, category, tags,
                auth_method, pricing_model, pricing_details,
                created_at, updated_at, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            agent_id, name, description, endpoint_url, "seed@agentseek.co", "AgentSeek Directory",
            website_url, logo_url, manifest, 0, trust_score,
            0, 0.95, 0, category, tags,
            auth_method, pricing_model, pricing_details,
            now, now, 1
        ))
        
        print(f"  ✅ {name} ({category}) — trust: {trust_score}")
        added += 1
    
    conn.commit()
    
    # Print updated category counts
    print(f"\n📊 Added: {added}, Skipped: {skipped}")
    print(f"\nUpdated category counts:")
    cursor.execute("SELECT category, COUNT(*) as cnt FROM agents WHERE active = 1 GROUP BY category ORDER BY cnt DESC")
    for row in cursor.fetchall():
        print(f"  {row[1]:3d}  {row[0]}")
    
    total = cursor.execute("SELECT COUNT(*) FROM agents WHERE active = 1").fetchone()[0]
    print(f"  ---\n  {total:3d}  TOTAL")
    
    conn.close()

if __name__ == "__main__":
    main()