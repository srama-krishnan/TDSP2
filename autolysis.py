# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pandas",
#   "matplotlib",
#   "seaborn",
#   "requests",
#   "chardet",
# ]
# ///

import os
import requests
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import chardet
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Set the API key and endpoint
API_KEY = os.environ.get("AIPROXY_TOKEN")
ENDPOINT = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"

if not API_KEY:
    raise ValueError("AIPROXY_TOKEN environment variable is not set.")

def query_llm(messages):
    """
    Query the LLM for analysis insights.
    Args:
        messages (list): A list of message dictionaries for the chat model.
    Returns:
        str: The response content from the model.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    data = {"model": "gpt-4o-mini", "messages": messages}

    response = requests.post(ENDPOINT, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")

def detect_and_load_csv(file_path):
    """
    Detect file encoding and load the CSV.
    Args:
        file_path (str): Path to the CSV file.
    Returns:
        pd.DataFrame: Loaded dataset.
    """
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)
        detected_encoding = chardet.detect(raw_data)['encoding']
        logging.info(f"Detected encoding: {detected_encoding}")
        return pd.read_csv(file_path, encoding=detected_encoding)
    except Exception as e:
        logging.warning(f"Error loading with detected encoding. Using ISO-8859-1. Error: {e}")
        return pd.read_csv(file_path, encoding='ISO-8859-1')

def generate_visualizations(df, output_dir):
    """
    Generate and save visualizations.
    Args:
        df (pd.DataFrame): The dataset.
        output_dir (str): Directory to save visualizations.
    Returns:
        list: Paths of saved visualizations.
    """
    visualizations = []
    numeric_df = df.select_dtypes(include=["number"])

    # Correlation Heatmap
    if numeric_df.shape[1] > 1:
        plt.figure(figsize=(8, 6))
        sns.heatmap(numeric_df.corr(), annot=True, fmt=".2f", cmap="coolwarm")
        plt.title("Correlation Heatmap")
        plt.xlabel("Numeric Columns")
        plt.ylabel("Numeric Columns")
        path = os.path.join(output_dir, "correlation_heatmap.png")
        plt.savefig(path, dpi=150)
        plt.close()
        visualizations.append(path)
        logging.info(f"Heatmap saved to: {path}")

    # Distribution Plot
    for col in numeric_df.columns[:2]:  # Limit to first 2 columns
        plt.figure(figsize=(8, 6))
        sns.histplot(numeric_df[col], kde=True, bins=20)
        plt.title(f"Distribution of {col}")
        plt.xlabel(col)
        plt.ylabel("Frequency")
        plt.legend([col])
        path = os.path.join(output_dir, f"{col}_distribution.png")
        plt.savefig(path, dpi=150)
        plt.close()
        visualizations.append(path)
        logging.info(f"Distribution saved to: {path}")

    return visualizations

def generate_report(df, summary, visualizations, output_dir):
    """
    Generate analysis report and insights.
    Args:
        df (pd.DataFrame): Dataset.
        summary (dict): Summary statistics and insights.
        visualizations (list): Paths to saved visualizations.
        output_dir (str): Directory to save the report.
    """
    # Improve the prompt with additional insights
    messages = [
        {"role": "system", "content": "You are a skilled data analyst. Provide detailed and structured insights."},
        {"role": "user", "content": f"""
        Dataset Details:
        - Columns: {summary['columns']}
        - Data Types: {summary['data_types']}
        - Missing Values: {summary['num_missing_values']}
        - Summary Statistics: {summary['summary_stats']}
        - Correlations: {df.corr().to_dict()}
        - Skewness: {df.skew(numeric_only=True).to_dict()}
        
        Provide:
        1. Key insights from the data.
        2. Patterns observed in numerical and categorical variables.
        3. Insights on missing values and correlations.
        4. Suggestions for further analysis.
        """}
    ]

    # Query the LLM for insights
    try:
        insights = query_llm(messages)
    except Exception as e:
        insights = f"Failed to generate insights using LLM: {e}"

    # Write README.md
    readme_path = os.path.join(output_dir, "README.md")
    with open(readme_path, "w") as f:
        f.write("# Analysis Report\n\n")
        f.write("## Dataset Overview\n")
        f.write(f"Rows: {len(df)}, Columns: {len(df.columns)}\n\n")
        f.write("### Columns:\n")
        for col in summary['columns']:
            f.write(f"- {col}\n")
        f.write("\n## Analysis Summary\n")
        f.write(insights + "\n\n")
        f.write("## Visualizations\n")
        for viz in visualizations:
            f.write(f"![{viz}]({viz})\n\n")
    logging.info(f"README.md written to: {readme_path}")

def analyze_and_generate_report(csv_file):
    """
    Main function to analyze data and generate report.
    """
    base_name = os.path.splitext(os.path.basename(csv_file))[0]
    output_dir = base_name
    os.makedirs(output_dir, exist_ok=True)

    # Load data
    df = detect_and_load_csv(csv_file)
    logging.info(f"Dataset loaded with {len(df)} rows and {len(df.columns)} columns.")

    # Data summary
    summary = {
        "columns": list(df.columns),
        "data_types": df.dtypes.to_dict(),
        "num_missing_values": df.isnull().sum().to_dict(),
        "summary_stats": df.describe(include="all").to_dict(),
    }

    # Generate visualizations
    visualizations = generate_visualizations(df, output_dir)

    # Generate report
    generate_report(df, summary, visualizations, output_dir)

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        logging.error("Usage: python autolysis.py <dataset.csv>")
        sys.exit(1)

    csv_filename = sys.argv[1]
    if not os.path.isfile(csv_filename):
        logging.error(f"Error: The file '{csv_filename}' does not exist.")
        sys.exit(1)

    analyze_and_generate_report(csv_filename)
