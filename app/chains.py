import os
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

class Chain:
    def __init__(self):
        self.llm = ChatGroq(temperature=0, groq_api_key=os.getenv("GROQ_API_KEY"), model_name="llama-3.1-70b-versatile")

    def extract_jobs(self, cleaned_text):
        prompt_extract = PromptTemplate.from_template(
            """
            ### SCRAPED TEXT FROM WEBSITE:
            {page_data}
            ### INSTRUCTION:
            The scraped text is from the career's page of a website.
            Your job is to extract the job postings and return them in JSON format containing the following keys: `role`, `experience`, `skills` and `description`.
            Only return the valid JSON.
            ### VALID JSON (NO PREAMBLE):
            """
        )
        chain_extract = prompt_extract | self.llm
        res = chain_extract.invoke(input={"page_data": cleaned_text})
        try:
            json_parser = JsonOutputParser()
            res = json_parser.parse(res.content)
        except OutputParserException:
            raise OutputParserException("Context too big. Unable to parse jobs.")
        return res if isinstance(res, list) else [res]

    def extract_company_name(self, job_url):
        """
        Extract company name from job URL
        """
        try:
            parsed_url = urlparse(job_url)
            # Remove 'www.' and split the domain
            domain_parts = parsed_url.netloc.replace('www.', '').split('.')
            
            # Take the first part of the domain as the company name
            company_name = domain_parts[0].capitalize()
            
            # Special handling for some common domains
            special_mappings = {
                'careers': 'Company',
                'jobs': 'Company',
                'hire': 'Company'
            }
            
            return special_mappings.get(company_name, company_name)
        except Exception:
            return "Potential Employer"

    def write_mail(self, job, links, user_name="Applicant", job_url=None):
        # Extract company name from URL if provided
        company_name = self.extract_company_name(job_url) if job_url else "Potential Employer"

        prompt_email = PromptTemplate.from_template(
            """
            ### JOB DESCRIPTION:
            {job_description}

            ### INSTRUCTION:
            You are {user_name}, a passionate and skilled professional directly applying for this role at {company_name}. 
            Write a personalized, concise cold email that:
            1. Demonstrates a clear understanding of the job requirements
            2. Highlights your most relevant skills and experiences
            3. Shows genuine interest in {company_name} and the specific role
            4. Includes 1-2 relevant portfolio links that showcase your capabilities
            5. Expresses enthusiasm to discuss how your skills can contribute to the company's goals

            Key Guidelines:
            - Be professional yet conversational
            - Focus on the value you can bring
            - Avoid generic statements
            - Show you've researched the role and company
            - Create a compelling narrative that connects your skills to their needs

            ### PORTFOLIO LINKS:
            {link_list}

            ### EMAIL (Direct and Personalized Approach):
            """
        )
        chain_email = prompt_email | self.llm
        res = chain_email.invoke(input={
            "job_description": job,
            "user_name": user_name,
            "company_name": company_name,
            "link_list": "\n".join([link[0]['links'] for link in links if link]) if links else "No specific portfolio links"
        })
        return res.content

if __name__ == "__main__":
    print(os.getenv("GROQ_API_KEY"))