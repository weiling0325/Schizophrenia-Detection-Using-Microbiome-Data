import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pickle
from dowhy import CausalModel
import os
import logging

logging.basicConfig(level=logging.DEBUG)

icon_path = "icon/schizophrenia_icon.png"
st.set_page_config(page_title="Schizophrenia Detection", page_icon=icon_path)

# Load the Random Forest model with the selected features
save_path = 'model/best_PyImpetus_random_forest_model.pkl'
with open(save_path, 'rb') as file:
    data = pickle.load(file)
rf_model = data['model']
selected_features_with_age = data['selected_features']
selected_bacteria_features = [feature for feature in selected_features_with_age if feature != 'age']

precompute_causal_effect=pd.read_csv('dataset/precompute_causal_effects_bacteria_diagnosis.csv')
precompute_causal_effect.columns = ['Bacteria', 'Causal Effect']

if "prediction_result" not in st.session_state:
    st.session_state.prediction_result = None

if "causal_graph" not in st.session_state:
    st.session_state.causal_graph = None

if "age" not in st.session_state:
    st.session_state.age = None

# Main title
st.title("Schizophrenia Detection Using Microbiome Data")

# Function to process the uploaded file
def display_patient_bacteria(data, schizo_bacteria_features):
  try:
    # Filter and process patient data
    patient_data = data[schizo_bacteria_features]
    patient_data_transposed = patient_data.T.reset_index()
    patient_data_transposed.columns = ['Bacteria Name', 'Bacteria Composition']
    st.markdown("""
      <style>
      table {
          font-size: 10px !important; /* Smaller font size */
          word-wrap: break-word; /* Enable word wrapping */
      }
      .dataframe tbody tr th {
          word-wrap: break-word;
          white-space: break-spaces; /* Split text if necessary */
      }
      </style>
    """, unsafe_allow_html=True)
    st.subheader("Patient’s Schizophrenia-Linked Microbiome Details:")
    st.table(patient_data_transposed)
  except Exception as e:
    st.error(f"An error occurred while processing the file: {str(e)}")


# Function to calculate and rank bacteria causal effect
def causal_effect_ranking(bacteria_features_input):
  positive_causal_effects = []
  negative_causal_effects = []
  for bacteria in bacteria_features_input.columns:
    if bacteria in precompute_causal_effect['Bacteria'].values:
      precomputed_value = precompute_causal_effect.loc[precompute_causal_effect['Bacteria'] == bacteria, 'Causal Effect'].values[0]
      # Calculate impact: Effect = Precomputed Causal Effect * Patient's Microbiome Composition
      impact = precomputed_value * bacteria_features_input[bacteria].values[0]
      if impact > 0:
        positive_causal_effects.append({'Bacteria': bacteria, 'Causal Effect': impact})
      elif impact < 0:
        negative_causal_effects.append({'Bacteria': bacteria, 'Causal Effect': impact})
  positive_causal_effects = pd.DataFrame(positive_causal_effects).sort_values(by='Causal Effect', ascending=False)
  negative_causal_effects = pd.DataFrame(negative_causal_effects).sort_values(by='Causal Effect', ascending=False)
  if len(positive_causal_effects) > 0:
    top_positive = positive_causal_effects.head(10)
  else :
    top_positive = positive_causal_effects
  if len(negative_causal_effects) > 0:
    top_negative = negative_causal_effects.tail(10)
  else:
    top_negative = negative_causal_effects
  top_effects = pd.concat([top_positive, top_negative]).sort_values(by='Causal Effect', ascending=False)
  display_causal_effect_ranking(top_effects)


# Function to visualize the bacteria causal effect
def display_causal_effect_ranking(causal_effects_df):
  # Create a mapping from bacteria names to generic labels
  bacteria_mapping = {bacteria: f"Bacteria {i+1}" for i, bacteria in enumerate(causal_effects_df['Bacteria'])}
  causal_effects_df['Bacteria Label'] = causal_effects_df['Bacteria'].map(bacteria_mapping)
  # Plot the causal effect ranking using the mapped labels
  plt.figure(figsize=(10, 5))
  barplot = sns.barplot(data=causal_effects_df, x='Causal Effect', y='Bacteria Label', palette="coolwarm")
  # Add causal effect measure inside the bars
  for bar, value in zip(barplot.patches, causal_effects_df['Causal Effect']):
    bar_width = bar.get_width()
    x_position = bar_width - 0.01 if value > 0 else bar_width + 0.01
    alignment = "left" if value > 0 else "right"
    barplot.annotate(
      f"{value:.4f}",
      (x_position, bar.get_y() + bar.get_height() / 2),  # Position inside the bar
      ha=alignment,
      va="center",
      fontsize=10,
      color="black"
    )
  plt.xlabel('Causal Effect Measure')
  plt.ylabel('Bacteria (Generic Labels)')
  plt.title('Top Positive and Negative Causal Effect Measures of Bacteria on Schizophrenia')
  plt.tight_layout()
  st.pyplot(plt)
  st.session_state.causal_graph = plt

  # Create a DataFrame for the legend
  legend_df = pd.DataFrame({
      'Bacteria Label': list(bacteria_mapping.values()),
      'Bacteria Name': list(bacteria_mapping.keys())
  })
  st.markdown("""
    <style>
    table {
        font-size: 10px !important; /* Smaller font size */
        word-wrap: break-word; /* Enable word wrapping */
    }
    .dataframe tbody tr th {
        word-wrap: break-word;
        white-space: break-spaces; /* Split text if necessary */
    }
    </style>
  """, unsafe_allow_html=True)
  st.markdown("**Bacteria Legend**")
  st.table(legend_df)


# Function to make predictions and display results
def predict(input_features):
  schizo_prediction = rf_model.predict(input_features)
  st.session_state.prediction_result = schizo_prediction
  st.subheader("Detection Result:")
  if schizo_prediction == 1:
    st.markdown("Schizophrenia is Detected")
    patient_bacteria_data = input_features.drop(columns=['age'])
    st.subheader("Causal Analysis:")
    causal_effect_ranking(patient_bacteria_data)
  else:
    st.markdown("Schizophrenia is Not Detected")

def reset_age():
  if 'age' in st.session_state:
    del st.session_state['age']  # Clear the age field when patient ID changes

def validate_age():
  if age < 1:
      st.error("Please enter a valid age.")
  if 'age' in st.session_state:
    if st.session_state['age'] is None:
      st.error("Please key in the patient's age.")

# File upload
try:
  input_file = st.file_uploader("Upload Microbiome Composition CSV or XLSX File", type=['csv', 'xlsx'], accept_multiple_files=False)
  if input_file is not None:
    # Check file size limit
    input_file.seek(0, os.SEEK_END)
    file_size = input_file.tell()
    input_file.seek(0)

    if file_size > 1 * 1024 * 1024 * 1024:
      st.error("File size exceeds the 1GB limit. Please upload a smaller file.")
    else:
      # Load the data
      data = pd.read_csv(input_file) if input_file.name.endswith('.csv') else pd.read_excel(input_file)

      # Ensure the file is not empty
      if data.empty:
          st.error("The uploaded file is empty. Please provide valid dataset.")
      else:
        # Ensure the dataset contains '#OTU ID' or 'sample-id'
        patient_id_column = '#OTU ID' if '#OTU ID' in data.columns else 'sample-id'
        if patient_id_column not in data.columns:
          st.error("No patient ID column found.")
        else:
          patient_ids = data[patient_id_column].unique()

          # Check for missing bacteria features
          missing_bacteria_features = [feature for feature in selected_bacteria_features if feature not in data.columns]

          if missing_bacteria_features:
            st.error(f"Missing required features: {', '.join(missing_bacteria_features)}.")
          else:
            # Dropdown for selecting a patient ID
            patient_id = st.selectbox("Select Patient ID", options=list(patient_ids), index=None, placeholder="Choose a Patient ID",key="patient_id", on_change=reset_age)

            if patient_id:
              selected_patient_data = data[data[patient_id_column] == patient_id]

              # Check for null values in the selected patient's data
              null_columns = selected_patient_data[selected_bacteria_features].isnull().any()
              if null_columns.any():
                null_features = selected_patient_data[selected_bacteria_features].columns[null_columns]
                st.error(f"Null values found in the following bacteria columns: {', '.join(null_features)}. Please provide a file with no missing values.")
              else:
                # Display patient microbiome table
                display_patient_bacteria(selected_patient_data, selected_bacteria_features)

                # Prompt for age input
                age = st.number_input("Enter Patient's Age", min_value=1, value=None, placeholder="Enter a whole number", key="age")
                selected_patient_data['age'] = age

                # Display detect button
                if st.button("Detect"):
                  # Validation checks
                  if st.session_state['age'] is None:
                    st.error("Please key in the patient's age.")
                  elif st.session_state['age'] < 1:
                    st.error("Please enter a valid age.")
                  else:
                    # Prepare input features
                    input_features = selected_patient_data[selected_features_with_age]

                    # Perform prediction
                    predict(input_features)
except Exception as e:
    st.error(f"An unexpected error occurred: {str(e)}")
