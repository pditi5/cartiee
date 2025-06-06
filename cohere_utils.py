import cohere
import os
from dotenv import load_dotenv
import re

load_dotenv()

# loading the api key from .env file
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
print("API KEY from env:", os.getenv("COHERE_API_KEY"))

co = cohere.ClientV2(COHERE_API_KEY)

def clean_sql(sql_code):
    """
    Removes markdown code fences and trims any explanation text before the actual SQL.
    """
    # removed markdown ```sql and ```
    sql_code = re.sub(r"```sql|```", "", sql_code).strip()
    
    # finding the actual SQL part (first line that starts with SELECT/UPDATE/DELETE/INSERT)
    sql_lines = sql_code.splitlines()
    for i, line in enumerate(sql_lines):
        if line.strip().upper().startswith(("SELECT", "INSERT", "UPDATE", "DELETE")):
            return "\n".join(sql_lines[i:]).strip()
    
    # if no SQL found, return entire block 
    return sql_code

# Prompt to convert natural language to SQL
def generate_sql_query(user_question):
    prompt = f"""
You are a helpful MySQL assistant for an e-commerce company. You are given 
a user's question and your job is to write a SQL query that runs on the 
following database 'ecommerce_db' with these tables:

- employee (employee_id, first_name, last_name, birthday, sex, salary, supervisor_id, branch_id)
- branch (branch_id, branch_name, manager_id, manager_startdate)
- client (client_id, first_name, last_name, branch_id)
- branch_supplier (branch_id, supplier_name, supplier_type)
- works_with (employee_id, client_id, total_sales, product_id)

Convert the natural language question into a MySQL query using proper table and column names.

User Question: {user_question}

SQL:
"""
    
    response = co.generate(
        model="command-r-plus",
        prompt=prompt,
        max_tokens=150,
        temperature=0.2,
        stop_sequences=["#", ";"]
    )
    
    sql_query = response.generations[0].text.strip()
    return clean_sql(sql_query)

def generate_natural_language_response(user_question, sql_query, query_results):
    """
    Converts SQL query results into natural language response using Cohere.
    
    Args:
        user_question (str): Original user question
        sql_query (str): Generated SQL query
        query_results (list): Results from database query
        
    Returns:
        str: Natural language response
    """
    # Convert results to a more readable format
    if not query_results:
        return "I couldn't find any data that matches your question."
    
    # Format results for the prompt
    results_text = ""
    for i, row in enumerate(query_results):
        results_text += f"Row {i+1}: {row}\n"
    
    prompt = f"""
You are a helpful assistant that explains database query results in natural, conversational language.

Original Question: {user_question}
SQL Query Used: {sql_query}
Query Results: 
{results_text}

Please provide a clear, natural language answer to the user's question based on these results. 
Be conversational and helpful. If there are multiple results, present them in an organized way.
Avoid technical jargon and make it easy to understand.

Natural Language Answer:
"""
    
    try:
        response = co.generate(
            model="command-r-plus",
            prompt=prompt,
            max_tokens=300,
            temperature=0.3
        )
        
        return response.generations[0].text.strip()
    
    except Exception as e:
        print(f"Error generating natural language response: {e}")
        return f"I found {len(query_results)} result(s) for your query, but couldn't generate a natural response."

def get_column_names_from_sql(sql_query):
    """
    Extract column names from SQL query to better format results.
    This is a simple implementation - you might want to make it more robust.
    """
    try:
        # Simple regex to find SELECT columns
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql_query, re.IGNORECASE | re.DOTALL)
        if select_match:
            columns_part = select_match.group(1).strip()
            if columns_part == '*':
                return None  # All columns selected
            else:
                # Split by comma and clean up
                columns = [col.strip() for col in columns_part.split(',')]
                return columns
    except:
        pass
    return None