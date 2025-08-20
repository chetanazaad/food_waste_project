# app.py
# Main script for the Local Food Wastage Management System

import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

# --- Configuration ---
# Define the name for the SQLite database file
DB_FILE = "food_waste_management.db"
# Define the directory where the CSV data files are located
DATA_DIR = "data"

# --- Database Functions ---

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        # Enable foreign key constraint enforcement
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as e:
        st.error(f"Database connection error: {e}")
        return None

def setup_database(conn):
    """
    Sets up the database. Creates tables and loads data from CSV files
    if the tables do not exist or are empty. This is a one-time setup.
    """
    cursor = conn.cursor()
    tables = {
        "Providers": "CREATE TABLE IF NOT EXISTS Providers (Provider_ID INTEGER PRIMARY KEY AUTOINCREMENT, Name TEXT, Type TEXT, Address TEXT, City TEXT, Contact TEXT);",
        "Receivers": "CREATE TABLE IF NOT EXISTS Receivers (Receiver_ID INTEGER PRIMARY KEY AUTOINCREMENT, Name TEXT, Type TEXT, City TEXT, Contact TEXT);",
        "Food_Listings": "CREATE TABLE IF NOT EXISTS Food_Listings (Food_ID INTEGER PRIMARY KEY AUTOINCREMENT, Food_Name TEXT, Quantity INTEGER, Expiry_Date DATE, Provider_ID INTEGER, Provider_Type TEXT, Location TEXT, Food_Type TEXT, Meal_Type TEXT, FOREIGN KEY (Provider_ID) REFERENCES Providers (Provider_ID) ON DELETE CASCADE);",
        "Claims": "CREATE TABLE IF NOT EXISTS Claims (Claim_ID INTEGER PRIMARY KEY AUTOINCREMENT, Food_ID INTEGER, Receiver_ID INTEGER, Status TEXT, Timestamp DATETIME, FOREIGN KEY (Food_ID) REFERENCES Food_Listings (Food_ID) ON DELETE CASCADE, FOREIGN KEY (Receiver_ID) REFERENCES Receivers (Receiver_ID) ON DELETE CASCADE);"
    }
    for table_name, schema in tables.items():
        cursor.execute(schema)
    for table_name in tables.keys():
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        if cursor.fetchone()[0] == 0:
            csv_file = os.path.join(DATA_DIR, f"{table_name.lower()}_data.csv")
            if os.path.exists(csv_file):
                try:
                    df = pd.read_csv(csv_file)
                    # Clean column names before inserting into SQL
                    df.columns = df.columns.str.strip()
                    df.to_sql(table_name, conn, if_exists='append', index=False)
                except Exception as e:
                    st.error(f"Error loading data for {table_name}: {e}")
    conn.commit()

# --- CRUD Functions ---
def add_provider(conn, name, p_type, address, city, contact):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Providers (Name, Type, Address, City, Contact) VALUES (?, ?, ?, ?, ?)", (name, p_type, address, city, contact))
    conn.commit()

def add_food_listing(conn, food_name, quantity, expiry_date, provider_id, provider_type, location, food_type, meal_type):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Food_Listings (Food_Name, Quantity, Expiry_Date, Provider_ID, Provider_Type, Location, Food_Type, Meal_Type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (food_name, quantity, expiry_date, provider_id, provider_type, location, food_type, meal_type))
    conn.commit()

def delete_listing(conn, food_id):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Food_Listings WHERE Food_ID = ?", (food_id,))
    conn.commit()

def delete_provider(conn, provider_id):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Providers WHERE Provider_ID = ?", (provider_id,))
    conn.commit()


# --- Main Application ---
def main():
    st.set_page_config(page_title="Food Waste Management", layout="wide")
    st.title("Local Food Wastage Management System")
    
    conn = get_db_connection()
    if conn:
        setup_database(conn)
    else:
        st.stop()

    st.sidebar.title("Dashboard Menu")
    page = st.sidebar.radio("Navigate the App", ["Home", "CRUD Operations", "Data Analysis"])

    if page == "Home":
        st.header("🏠 Home Dashboard")
        st.write("Welcome! This system helps manage and distribute surplus food efficiently.")
        st.info("Use the sidebar to navigate to different sections of the application.")
        st.subheader("Preview of Available Food Listings")
        try:
            food_df = pd.read_sql_query("SELECT * FROM Food_Listings LIMIT 10;", conn)
            st.dataframe(food_df)
        except Exception as e:
            st.error(f"Could not retrieve food listings: {e}")

    elif page == "CRUD Operations":
        st.header("📝 Manage Records (CRUD)")
        
        tab1, tab2, tab3 = st.tabs(["Add Records", "View Records", "Delete Records"])

        with tab1:
            st.subheader("Add a New Food Provider")
            with st.form("add_provider_form", clear_on_submit=True):
                p_name = st.text_input("Provider Name")
                p_type = st.selectbox("Provider Type", ["Restaurant", "Grocery Store", "Supermarket", "Individual"])
                p_address = st.text_input("Address")
                p_city = st.text_input("City")
                p_contact = st.text_input("Contact (Phone/Email)")
                submitted_provider = st.form_submit_button("Add Provider")
                if submitted_provider:
                    add_provider(conn, p_name, p_type, p_address, p_city, p_contact)
                    st.success("Provider added successfully!")

            st.divider()

            st.subheader("Add a New Food Listing")
            with st.form("add_food_listing_form", clear_on_submit=True):
                provider_list = pd.read_sql_query("SELECT Provider_ID, Name FROM Providers", conn)
                provider_dict = dict(zip(provider_list['Name'], provider_list['Provider_ID']))
                
                selected_provider_name = st.selectbox("Select Provider", provider_list['Name'])
                food_name = st.text_input("Food Item Name")
                quantity = st.number_input("Quantity", min_value=1, step=1)
                expiry_date = st.date_input("Expiry Date")
                
                provider_id = provider_dict.get(selected_provider_name)
                provider_details = pd.read_sql_query(f"SELECT Type, City FROM Providers WHERE Provider_ID = {provider_id}", conn) if provider_id else None
                
                provider_type = provider_details['Type'][0] if provider_details is not None and not provider_details.empty else ""
                location = provider_details['City'][0] if provider_details is not None and not provider_details.empty else ""

                food_type = st.selectbox("Food Type", ["Vegetarian", "Non-Vegetarian", "Vegan"])
                meal_type = st.selectbox("Meal Type", ["Breakfast", "Lunch", "Dinner", "Snacks"])

                submitted_listing = st.form_submit_button("Add Food Listing")
                if submitted_listing:
                    add_food_listing(conn, food_name, quantity, expiry_date, provider_id, provider_type, location, food_type, meal_type)
                    st.success("Food listing added successfully!")
        
        with tab2:
            st.subheader("View All Food Listings")
            all_listings = pd.read_sql_query("SELECT * FROM Food_Listings ORDER BY Expiry_Date ASC", conn)
            st.dataframe(all_listings)
            
            st.subheader("View All Providers")
            all_providers = pd.read_sql_query("SELECT * FROM Providers", conn)
            st.dataframe(all_providers)

        with tab3:
            st.subheader("Delete a Food Listing")
            listing_list = pd.read_sql_query("SELECT Food_ID, Food_Name, Location FROM Food_Listings", conn)
            listing_options = {f"{row['Food_Name']} (ID: {row['Food_ID']}) in {row['Location']}": row['Food_ID'] for index, row in listing_list.iterrows()}
            
            selected_listing_str = st.selectbox("Select Listing to Delete", options=listing_options.keys())
            if st.button("Delete Selected Listing"):
                listing_id_to_delete = listing_options[selected_listing_str]
                delete_listing(conn, listing_id_to_delete)
                st.success(f"Listing '{selected_listing_str}' has been deleted.")
                st.rerun()

            st.divider()

            st.subheader("Delete a Provider")
            st.warning("Warning: Deleting a provider will also delete all of their associated food listings.")
            provider_list_del = pd.read_sql_query("SELECT Provider_ID, Name FROM Providers", conn)
            provider_options_del = {f"{row['Name']} (ID: {row['Provider_ID']})": row['Provider_ID'] for index, row in provider_list_del.iterrows()}

            selected_provider_str = st.selectbox("Select Provider to Delete", options=provider_options_del.keys())
            if st.button("Delete Selected Provider"):
                provider_id_to_delete = provider_options_del[selected_provider_str]
                delete_provider(conn, provider_id_to_delete)
                st.success(f"Provider '{selected_provider_str}' and all associated listings have been deleted.")
                st.rerun()

    elif page == "Data Analysis":
        st.header("📊 Data Analysis & Insights")
        st.write("This section displays the analysis based on the SQL queries.")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("1. Provider and Receiver Counts by City")
            providers_by_city = pd.read_sql_query("SELECT City, COUNT(Provider_ID) AS NumberOfProviders FROM Providers GROUP BY City ORDER BY NumberOfProviders DESC;", conn)
            receivers_by_city = pd.read_sql_query("SELECT City, COUNT(Receiver_ID) AS NumberOfReceivers FROM Receivers GROUP BY City ORDER BY NumberOfReceivers DESC;", conn)
            city_counts = pd.merge(providers_by_city, receivers_by_city, on="City", how="outer").fillna(0)
            st.dataframe(city_counts, height=250)
            st.subheader("2. Top Contributing Food Provider Type")
            top_provider_type = pd.read_sql_query("SELECT p.Type, SUM(fl.Quantity) AS TotalQuantityDonated FROM Providers p JOIN Food_Listings fl ON p.Provider_ID = fl.Provider_ID GROUP BY p.Type ORDER BY TotalQuantityDonated DESC LIMIT 1;", conn)
            if not top_provider_type.empty:
                st.metric(label="Top Contributor (by Quantity)", value=top_provider_type['Type'][0], delta=f"{int(top_provider_type['TotalQuantityDonated'][0])} units donated")
            st.subheader("4. Total Quantity of Available Food")
            total_quantity_available = pd.read_sql_query("SELECT SUM(Quantity) AS TotalQuantity FROM Food_Listings;", conn)
            if not total_quantity_available.empty:
                st.metric(label="Total Food Units Available Now", value=f"{int(total_quantity_available['TotalQuantity'][0])}")
        with col2:
            st.subheader("3. Find Provider Contact Information by City")
            city_list = pd.read_sql_query("SELECT DISTINCT City FROM Providers ORDER BY City;", conn)['City'].tolist()
            selected_city = st.selectbox("Select a City", city_list)
            if selected_city:
                provider_contacts = pd.read_sql_query(f"SELECT Name AS ProviderName, Contact, Address FROM Providers WHERE City = '{selected_city}';", conn)
                st.dataframe(provider_contacts, height=250)
            st.subheader("5. City with the Most Food Listings")
            city_listings = pd.read_sql_query("SELECT Location, COUNT(Food_ID) AS NumberOfListings FROM Food_Listings GROUP BY Location ORDER BY NumberOfListings DESC LIMIT 1;", conn)
            if not city_listings.empty:
                st.metric(label="Most Active City", value=city_listings['Location'][0], delta=f"{int(city_listings['NumberOfListings'][0])} listings")
        st.divider()
        col3, col4 = st.columns(2)
        with col3:
            st.subheader("6. Most Common Food Types")
            common_food_types = pd.read_sql_query("SELECT Food_Type, COUNT(Food_ID) AS Count FROM Food_Listings GROUP BY Food_Type ORDER BY Count DESC;", conn)
            st.bar_chart(common_food_types.set_index('Food_Type'))
            st.subheader("9. Provider with Most Successful Claims")
            successful_claims = pd.read_sql_query("SELECT p.Name, COUNT(c.Claim_ID) AS SuccessfulClaims FROM Claims c JOIN Food_Listings fl ON c.Food_ID = fl.Food_ID JOIN Providers p ON fl.Provider_ID = p.Provider_ID WHERE c.Status = 'Completed' GROUP BY p.Name ORDER BY SuccessfulClaims DESC LIMIT 5;", conn)
            st.dataframe(successful_claims)
        with col4:
            st.subheader("7. Top 10 Most Claimed Food Items")
            claims_per_item = pd.read_sql_query("SELECT fl.Food_Name, COUNT(c.Claim_ID) AS NumberOfClaims FROM Claims c JOIN Food_Listings fl ON c.Food_ID = fl.Food_ID GROUP BY fl.Food_Name ORDER BY NumberOfClaims DESC LIMIT 10;", conn)
            st.dataframe(claims_per_item)
            st.subheader("10. Distribution of Claim Statuses")
            claim_status = pd.read_sql_query("SELECT Status, COUNT(Claim_ID) AS Count FROM Claims GROUP BY Status;", conn)
            st.bar_chart(claim_status.set_index('Status'))
        st.divider()
        col5, col6 = st.columns(2)
        with col5:
            st.subheader("12. Most Claimed Meal Types (All Claims)")
            meal_type_claims = pd.read_sql_query("SELECT fl.Meal_Type, COUNT(c.Claim_ID) as ClaimCount FROM Claims c JOIN Food_Listings fl ON c.Food_ID = fl.Food_ID GROUP BY fl.Meal_Type ORDER BY ClaimCount DESC;", conn)
            st.bar_chart(meal_type_claims.set_index('Meal_Type'))
        with col6:
            st.subheader("13. Total Food Donated per Provider")
            provider_donations = pd.read_sql_query("SELECT p.Name, SUM(fl.Quantity) as TotalQuantity FROM Providers p JOIN Food_Listings fl ON p.Provider_ID = fl.Provider_ID GROUP BY p.Name ORDER BY TotalQuantity DESC LIMIT 10;", conn)
            st.dataframe(provider_donations)
        
        # --- NEW ANALYSIS SECTION ---
        st.divider()
        st.subheader("Additional Insights")
        col7, col8 = st.columns(2)

        with col7:
            st.subheader("14. Provider with Most Listings (by Count)")
            provider_listings = pd.read_sql_query("""
                SELECT Provider_Type, COUNT(Food_ID) AS NumberOfListings
                FROM Food_Listings
                GROUP BY Provider_Type
                ORDER BY NumberOfListings DESC;
            """, conn)
            
            if not provider_listings.empty:
                top_provider = provider_listings.iloc[0]
                st.metric(label=f"Top Provider: {top_provider['Provider_Type']}", value=f"{top_provider['NumberOfListings']} listings")
                with st.expander("See full breakdown of listings by provider"):
                    st.dataframe(provider_listings)

        with col8:
            st.subheader("15. Most Successfully Claimed Meal Type")
            most_claimed_meal = pd.read_sql_query("""
                SELECT fl.Meal_Type, COUNT(c.Claim_ID) as ClaimCount
                FROM Claims c
                JOIN Food_Listings fl ON c.Food_ID = fl.Food_ID
                WHERE c.Status = 'Completed'
                GROUP BY fl.Meal_Type
                ORDER BY ClaimCount DESC;
            """, conn)

            if not most_claimed_meal.empty:
                top_meal = most_claimed_meal.iloc[0]
                st.metric(label=f"Top Meal: {top_meal['Meal_Type']}", value=f"{top_meal['ClaimCount']} successful claims")
                with st.expander("See full breakdown of successful claims"):
                    st.dataframe(most_claimed_meal)


    conn.close()

if __name__ == "__main__":
    if not os.path.isdir(DATA_DIR):
        st.error(f"Data directory not found! Please create a '{DATA_DIR}' folder and place your CSV files in it.")
    else:
        main()
