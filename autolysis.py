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

# Set the API key and endpoint
API_KEY = os.environ.get("AIPROXY_TOKEN")
ENDPOINT = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"

if not API_KEY:
    raise ValueError("AIPROXY_TOKEN environment variable is not set.")

def query_llm(messages):
    """
    Send a request to the AI Proxy for chat completions.

    Args:
        messages (list): A list of message dictionaries for the chat model.

    Returns:
        str: The response content from the model.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    data = {
        "model": "gpt-4o-mini",
        "messages": messages
    }

    response = requests.post(ENDPOINT, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")

def detect_and_load_csv(file_path):
    """
    Detects the encoding of a CSV file and loads it with a fallback to ISO-8859-1 if needed.

    Args:
        file_path (str): Path to the CSV file.

    Returns:
        pd.DataFrame: Loaded DataFrame.
    """
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)
        detected_encoding = chardet.detect(raw_data)['encoding']
        print(f"Detected encoding: {detected_encoding}")
        return pd.read_csv(file_path, encoding=detected_encoding)
    except Exception as e:
        print(f"Failed to load with detected encoding. Falling back to ISO-8859-1. Error: {e}")
        return pd.read_csv(file_path, encoding='ISO-8859-1')

def analyze_and_generate_report(csv_file):
    # Create a directory based on the CSV file name (without extension)
    base_name = os.path.splitext(os.path.basename(csv_file))[0]
    output_dir = base_name
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Load the dataset
        df = detect_and_load_csv(csv_file)
        print(f"Dataset loaded: {len(df)} rows, {len(df.columns)} columns")
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        return

    # Dataset summary
    summary = {
        "columns": list(df.columns),
        "data_types": df.dtypes.to_dict(),
        "num_rows": len(df),
        "num_missing_values": df.isnull().sum().to_dict(),
        "summary_stats": df.describe(include="all").to_dict(),
    }
    print("Dataset summary prepared.")

    # Create visualizations
    visualizations = []
    numeric_df = df.select_dtypes(include=["number"])

    # Visualization 1: Correlation Heatmap
    if numeric_df.shape[1] > 1:
        plt.figure(figsize=(6, 6))
        sns.heatmap(numeric_df.corr(), annot=True, fmt=".2f", cmap="coolwarm")
        plt.title("Correlation Heatmap")
        heatmap_path = os.path.join(output_dir, "correlation_heatmap.png")
        plt.savefig(heatmap_path, dpi=150)
        visualizations.append(heatmap_path)
        plt.close()
        print(f"Heatmap saved to: {heatmap_path}")

    # Visualization 2: Distribution of First Numeric Column
    if not numeric_df.empty:
        plt.figure(figsize=(6, 6))
        sns.histplot(numeric_df.iloc[:, 0], kde=True, bins=20)
        plt.title(f"Distribution of {numeric_df.columns[0]}")
        dist_path = os.path.join(output_dir, "distribution.png")
        plt.savefig(dist_path, dpi=150)
        visualizations.append(dist_path)
        plt.close()
        print(f"Distribution plot saved to: {dist_path}")

    # Visualization 3: Boxplot
    categorical_df = df.select_dtypes(include=["object"])
    if not numeric_df.empty and not categorical_df.empty:
        first_category = categorical_df.columns[0]
        plt.figure(figsize=(6, 6))
        sns.boxplot(x=first_category, y=numeric_df.columns[0], data=df)
        plt.title(f"Boxplot of {numeric_df.columns[0]} by {first_category}")
        boxplot_path = os.path.join(output_dir, "boxplot.png")
        plt.savefig(boxplot_path, dpi=150)
        visualizations.append(boxplot_path)
        plt.close()
        print(f"Boxplot saved to: {boxplot_path}")

    # Generate insights and narration using LLM
    try:
        messages = [
            {"role": "system", "content": "You are a data analysis assistant."},
            {"role": "user", "content": f"Summarize and analyze this dataset. Columns: {summary['columns']}\n"}
        ]
        narration = query_llm(messages)
    except Exception as e:
        narration = f"Failed to generate insights using LLM: {e}"

    # Write README.md
    readme_path = os.path.join(output_dir, "README.md")
    with open(readme_path, "w") as readme_file:
        readme_file.write("# **Analysis Report**\n\n")
        readme_file.write("## **Dataset Overview**\n")
        readme_file.write(f"The dataset contains {len(df)} rows and {len(df.columns)} columns. Below is a summary of the data:\n\n")
        readme_file.write("### Columns:\n")
        for col in summary['columns']:
            readme_file.write(f"- {col}\n")
        readme_file.write("\n")

        readme_file.write("## **Analysis Summary**\n")
        readme_file.write(narration + "\n\n")

        readme_file.write("## **Visualizations**\n")
        for viz in visualizations:
            readme_file.write(f"### {viz.replace('.png', '').capitalize()}:\n")
            readme_file.write(f"![{viz}]({viz})\n\n")
    print(f"README.md written to: {readme_path}")

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python autolysis.py <dataset.csv>")
        sys.exit(1)

    csv_filename = sys.argv[1]

    if not os.path.isfile(csv_filename):
        print(f"Error: The file '{csv_filename}' does not exist.")
        sys.exit(1)

    analyze_and_generate_report(csv_filename)
