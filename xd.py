import streamlit as st
import pandas as pd
from fuzzywuzzy import process

def get_product_quantity_category(quantity):
    # Function remains unchanged
    if quantity < 100:
        return '1'
    elif quantity < 250:
        return '2'
    elif quantity < 500:
        return '3'
    elif quantity < 1000:
        return '4'
    elif quantity < 1500:
        return '5'
    else:
        return '6'

def get_print_quantity_category(quantity):
    # Function remains unchanged
    if quantity < 50:
        return '1'
    elif quantity < 100:
        return '50'
    elif quantity < 250:
        return '100'
    elif quantity < 500:
        return '250'
    elif quantity < 1000:
        return '500'
    elif quantity < 2500:
        return '1000'
    elif quantity < 5000:
        return '2500'
    else:
        return '5000'

def calculate_total_print_cost(selected_print, quantity):
    # Function remains unchanged
    setup_charge = float(selected_print['SetupNet'].values[0])
    applicable_deco_price = selected_print[f'PrintPriceNet_{get_print_quantity_category(quantity)}'].values[0]
    total_print_cost = setup_charge + quantity * applicable_deco_price
    return total_print_cost

def main():
    st.title("XD Connects Calculator")

    product_price_feed_df = pd.read_csv("https://github.com/sunsuzy/xd/blob/eedd91ae6153a03de0658ec61b099d8cd8648468/Xindao.V2.ProductPrices-nl-nl-C26907%20(1).txt", delimiter='\t')
    print_price_feed_df = pd.read_csv("C:/Users/Sundeep.CSE/Environments/Test/my_env/Xindao.V2.PrintPrices-nl-nl-C26907.txt", delimiter='\t')

    descriptions = product_price_feed_df['ItemName'].unique()
    query = st.text_input('Search for a product or enter an item code')
    if query:
        matched_items = product_price_feed_df[product_price_feed_df['ItemCode'].astype(str).str.lower() == str(query).lower()]
        if not matched_items.empty:
            descriptions = [matched_items['ItemName'].values[0]]
        else:
            closest_matches = process.extract(query, descriptions, limit=10)
            descriptions = [match[0] for match in closest_matches]
    else:
        descriptions = []
    description = st.selectbox('Select a product', descriptions)

    matched_products = product_price_feed_df[product_price_feed_df['ItemName'] == description]
    if not matched_products.empty:
        item_code = matched_products['ItemCode'].values[0]
        st.write(f"Item Code: {item_code}")

        selected_product = product_price_feed_df[product_price_feed_df['ItemCode'] == item_code].copy()

        available_print_techniques = selected_product['AllPrintCodes'].values[0].split(',')
        print_techniques_with_names = []
        for technique in available_print_techniques:
            technique_df = print_price_feed_df[print_price_feed_df['PrintCode'] == technique]
            if not technique_df.empty:
                print_techniques_with_names.append((technique, technique_df['PrintTechnique'].values[0]))
        print_technique = st.selectbox('Select a print technique', options=print_techniques_with_names, format_func=lambda x: f"{x[0]} - {x[1]}")

        selected_print_technique = print_price_feed_df[print_price_feed_df['PrintCode'] == print_technique[0]]
        selected_print_technique['NrOfColors'] = pd.to_numeric(selected_print_technique['NrOfColors'], errors='coerce')

        # Adding the dropdown for selecting the preferred print area
        if print_technique[0] in ['Embroidery', 'Embroidery 3D', 'Embroidery badge', 'Hot Stamping', 'Leather badge', 'Printed badge']:
            print_areas = selected_print_technique['PrintArea'].dropna().unique()
            preferred_print_area = st.selectbox('Select preferred print area', options=print_areas, index=0)
            selected_print_technique = selected_print_technique[selected_print_technique['PrintArea'] == preferred_print_area]

        available_colors = selected_print_technique['NrOfColors'].dropna().unique()
        available_colors = [str(int(color)) if not pd.isna(color) else 'None' for color in available_colors]
        print_colors = st.selectbox('Enter the number of print colors', options=available_colors, index=len(available_colors) - 1)

        quantity = st.number_input('Enter quantity', min_value=1)

        applicable_price_bar = int(selected_product[f'Qty{get_product_quantity_category(quantity)}'].values[0])
        applicable_nett_price = selected_product[f'ItemPriceNet_Qty{get_product_quantity_category(quantity)}'].values[0]

        total_product_cost = quantity * applicable_nett_price

        if print_colors is None:
            number_of_colors = None
        else:
            number_of_colors = int(float(print_colors))

        # Select print with matching color number or where 'NrOfColors' is NaN
        selected_print = selected_print_technique[(selected_print_technique['NrOfColors'].isna()) | 
                                                  (selected_print_technique['NrOfColors'] == number_of_colors)]

        # If 'NrOfColors' is NaN, look at 'PrintArea'
        if selected_print['NrOfColors'].isna().all():
            if selected_print['PrintArea'].isna().all():  # If 'PrintArea' is also NaN, return the first row
                selected_print = selected_print.iloc[0:1]
            else:  # If 'PrintArea' is not NaN, select rows with not NaN 'PrintArea'
                selected_print = selected_print[selected_print['PrintArea'].notna()]

        if selected_print.empty:
            st.error(f"No print technique found with {print_colors} colors.")
            return

        total_print_cost = calculate_total_print_cost(selected_print, quantity)

        total_cost_excl_shipping = total_product_cost + total_print_cost
        shipping_cost = 16.95 if total_product_cost < 500 else 0
        total_cost_incl_shipping = total_cost_excl_shipping + shipping_cost

        kostprijs = total_cost_incl_shipping / quantity

        margin = st.slider('Enter margin (0-100)', min_value=0, max_value=100, value=38)

        sell_price = kostprijs / (1 - (margin / 100))

        cost_breakdown_data = {
            'Cost Component': ['Productkosten', 'Decoratiekosten (inclusief setup)', 'Totaal excl. verzending', 'Verzendkosten', 'Totaal'],
            'Amount': [total_product_cost, total_print_cost, total_cost_excl_shipping, shipping_cost, total_cost_incl_shipping]
        }

        cost_breakdown_df = pd.DataFrame(cost_breakdown_data)
        cost_breakdown_df['Amount'] = cost_breakdown_df['Amount'].apply(lambda x: '€ {:.2f}'.format(x))

        st.write('Kostenoverzicht:')
        st.table(cost_breakdown_df)

        st.markdown(f"<p style='color:red'>**Kostprijs: € {kostprijs:.2f}**</p>", unsafe_allow_html=True)
        
        st.markdown(f"**Verkoopprijs: € {sell_price:.2f}**")
    else:
        st.write('No matching products found.')

if __name__ == "__main__":
    main()
