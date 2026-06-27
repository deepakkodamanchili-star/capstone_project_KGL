from mcp.server.fastmcp import FastMCP
import json
import logging

mcp = FastMCP("LeadSift Tools")

@mcp.tool()
def search_web_profiles(name: str, company: str) -> str:
    """Search professional web and social networks to gather profile details for a lead.
    
    Args:
        name: The full name of the lead.
        company: The company they work for.
    """
    logging.info(f"Searching web profiles for {name} at {company}")
    # Mock search response
    return json.dumps({
        "status": "success",
        "profiles": [
            {
                "platform": "LinkedIn",
                "title": "Director of Product & Innovation",
                "duration": "3 years",
                "skills": ["Enterprise AI", "Product Strategy", "CRM Integrations"]
            },
            {
                "platform": "GitHub",
                "username": name.lower().replace(" ", ""),
                "public_repos": 24,
                "languages": ["Python", "Go", "TypeScript"]
            }
        ]
    })

@mcp.tool()
def fetch_company_details(company: str) -> str:
    """Fetch structured firmographic details for a company to aid lead qualification.
    
    Args:
        company: The name of the company.
    """
    logging.info(f"Fetching company details for {company}")
    company_lower = company.lower()
    # Mock firmographics lookup
    if "google" in company_lower:
        size = 180000
        industry = "Technology"
    elif "stripe" in company_lower:
        size = 8000
        industry = "Fintech"
    elif "smallbiz" in company_lower or "startup" in company_lower:
        size = 25
        industry = "E-commerce"
    else:
        size = 450
        industry = "Software / SaaS"
        
    return json.dumps({
        "company_name": company,
        "employee_count": size,
        "industry": industry,
        "revenue_estimate": f"${size * 150000:,} USD",
        "hq_location": "San Francisco, CA"
    })

@mcp.tool()
def write_to_crm(name: str, email: str, company: str, score: int, rationale: str) -> str:
    """Enrich the lead record and write the finalized details to the CRM database.
    
    Args:
        name: Name of the lead.
        email: Email address of the lead.
        company: Company name.
        score: Computed lead score (0-100).
        rationale: Scoring rationale.
    """
    logging.info(f"Writing lead {name} to CRM with score {score}")
    return json.dumps({
        "status": "success",
        "crm_id": f"crm_lead_{abs(hash(email)) % 10000000}",
        "message": f"Successfully enriched and saved lead {name} of {company} with score {score}."
    })

if __name__ == "__main__":
    mcp.run()
