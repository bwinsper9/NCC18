
import streamlit as st
import pandas as pd
import random
import time
from fpdf import FPDF
import tempfile

st.set_page_config(page_title="Catering Companion", layout="centered", page_icon="🍴")

# Load style
try:
    st.markdown(open("sexy_minimal_ui_style_snippet.html").read(), unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("UI style sheet not found. Using default styling.")

# App setup
affirmations = [
    "You're doing great work, keep pushing.",
    "Today's prep is tomorrow's peace.",
    "Every tray you prep is a step closer to success.",
]

# Pantry checkbox tracking
if "checked_ingredients" not in st.session_state:
    st.session_state.checked_ingredients = set()

# --- Insert checkbox logic in shopping list preview section ---
def show_shopping_list_preview(recipe_df):
    st.subheader("Shopping List Preview")
    for idx, row in recipe_df.iterrows():
        label = f"{row['ScaledQuantity']} {row['Unit']} {row['Ingredient']}"
        key = f"checkbox_{row['Ingredient']}_{idx}"
        if st.checkbox(label, key=key):
            st.session_state.checked_ingredients.add(row["Ingredient"])
        else:
            st.session_state.checked_ingredients.discard(row["Ingredient"])
    return recipe_df[~recipe_df["Ingredient"].isin(st.session_state.checked_ingredients)]

def generate_shopping_list_pdf(sections):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for category, lines in sections.items():
        title = category[0] if isinstance(category, tuple) else category
        pdf.set_font("Arial", "B", 14)
        pdf.cell(200, 10, txt=title.upper(), ln=True)
        pdf.set_font("Arial", size=12)
        for line in lines:
            pdf.cell(200, 10, txt=f"[ ] {line}", ln=True)
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_pdf.name)
    return temp_pdf.name

def generate_recipe_guides_pdf(recipe_guides):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    for recipe_name, (ingredients_list, method_text) in recipe_guides.items():
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(200, 10, txt=recipe_name.upper(), ln=True, align="C")
        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 10, txt="Ingredients:", ln=True)
        pdf.set_font("Arial", size=12)
        for qty, unit, item in ingredients_list:
            if isinstance(qty, float) and qty.is_integer():
                qty = int(qty)
            pdf.cell(200, 10, txt=f"- {qty} {unit} {item}", ln=True)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 10, txt="Method:", ln=True)
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, method_text)
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_pdf.name)
    return temp_pdf.name

try:
    recipes_df = pd.read_csv("master_recipe_template.csv")
    recipes_df = recipes_df.dropna(subset=["Quantity", "BaseServings"])
    recipes_df = recipes_df[pd.to_numeric(recipes_df["Quantity"], errors="coerce").notnull()]
    recipes_df = recipes_df[pd.to_numeric(recipes_df["BaseServings"], errors="coerce").notnull()]
    recipes_df["Quantity"] = recipes_df["Quantity"].astype(float)
    recipes_df["BaseServings"] = recipes_df["BaseServings"].astype(int)

    available_recipes = sorted(recipes_df["RecipeName"].unique())
    guests = st.number_input("Number of guests", min_value=1, step=1)
    selected = st.multiselect("Select recipes", options=available_recipes)

    if st.button("Generate Plan") and selected and guests > 0:
        st.session_state.generated = True
        st.session_state.sections = {}
        st.session_state.recipe_guides = {}

        combined_scaled = pd.DataFrame()
        individual_scaled = {}
        methods = {}

        for recipe_name in selected:
            data = recipes_df[recipes_df["RecipeName"].str.lower() == recipe_name.lower()]
            base_servings = data["BaseServings"].iloc[0]
            if base_servings == 0:
                st.error(f"Recipe '{recipe_name}' has BaseServings set to 0. Skipping.")
                continue

            scale_factor = guests / base_servings
            data["ScaledQuantity"] = data["Quantity"] * scale_factor
            combined_scaled = pd.concat([combined_scaled, data], ignore_index=True)
            individual_scaled[recipe_name] = data
            methods[recipe_name] = data["Method"].iloc[0]

        combined_scaled = combined_scaled.groupby(["Ingredient", "Unit", "Category"], as_index=False).sum()
        for category, group in combined_scaled.groupby(["Category"]):
            lines = []
            for _, row in group.sort_values("Ingredient").iterrows():
                qty = round(row["ScaledQuantity"], 2)
                if qty.is_integer():
                    qty = int(qty)
                lines.append(f"{qty} {row['Unit']} {row['Ingredient']}")
            st.session_state.sections[category] = lines

        for recipe_name, scaled_data in individual_scaled.items():
            ingredients_list = []
            for _, row in scaled_data.iterrows():
                qty = round(row["ScaledQuantity"], 2)
                if qty.is_integer():
                    qty = int(qty)
                ingredients_list.append((qty, row["Unit"], row["Ingredient"]))
            st.session_state.recipe_guides[recipe_name] = (ingredients_list, methods[recipe_name])

except Exception as e:
    st.error(f"An error occurred: {e}")

# Display preview and download if available
if st.session_state.get("generated"):
    st.markdown("### ✅ Shopping List and Recipe Guides have been generated.")
    st.markdown("## 🛒 Shopping List Preview")
    for i, (category, lines) in enumerate(st.session_state.sections.items()):
        st.markdown(f"### {(category[0] if isinstance(category, tuple) else category).upper()}")
        for j, line in enumerate(lines):
            st.checkbox(line, value=False, key=f"{line}_{i}_{j}")

    st.markdown("---")
    st.markdown("## 📋 Recipe Guides Preview")
    for recipe_name, (ingredients_list, method_text) in st.session_state.recipe_guides.items():
        st.markdown(f"### {recipe_name.upper()}")
        st.markdown("#### Ingredients:")
        for qty, unit, item in ingredients_list:
            st.markdown(f"- {qty} {unit} {item}")
        st.markdown("#### Method:")
        st.markdown(method_text)
        st.markdown("---")

    shopping_pdf = generate_shopping_list_pdf(st.session_state.sections)
    guide_pdf = generate_recipe_guides_pdf(st.session_state.recipe_guides)
    with open(shopping_pdf, "rb") as f:
        st.download_button("📥 Download Shopping List PDF", f, "shopping_list.pdf")
    with open(guide_pdf, "rb") as f:
        st.download_button("📥 Download Recipe Guides PDF", f, "recipe_guides.pdf")
