import streamlit as st
import pandas as pd
from fuzzywuzzy import process

def get_product_price_tier(product, quantity):
    qty_cols = ['Qty1', 'Qty2', 'Qty3', 'Qty4', 'Qty5', 'Qty6']
    if quantity >= product[qty_cols[-1]].iloc[0]:
        return qty_cols[-1]
    for i in range(1, len(qty_cols)):
        if quantity < product[qty_cols[i]].iloc[0]:
            return qty_cols[i - 1]
    return qty_cols[-1]

def get_product_tier_price(product, tier):
    tier_number = int(tier[3:])
    price_tiers = [f'ItemPriceNet_Qty{i}' for i in range(1, 7)]
    tier = min(tier_number, len(price_tiers))
    for i in range(tier - 1, -1, -1):
        price_col = price_tiers[i]
        price = product[price_col].values[0]
        if pd.notna(price):
            return price
    # If the requested tier is missing, return the price from ItemPriceNet_Qty1 if available
    if pd.notna(product['ItemPriceNet_Qty1'].values[0]):
        return product['ItemPriceNet_Qty1'].values[0]
    return None

def get_print_quantity_category(quantity):
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
    setup_charge = float(selected_print['SetupNet'].values[0])
    applicable_deco_price = selected_print[f'PrintPriceNet_{get_print_quantity_category(quantity)}'].values[0]
    total_print_cost = setup_charge + quantity * applicable_deco_price
    return total_print_cost

def get_max_colors_for_print_code(print_code, item_code, print_data_df):
    max_colors_row = print_data_df[(print_data_df['PrintCode'] == print_code) & (print_data_df['ItemCode'] == item_code)]
    if not max_colors_row.empty:
        return max_colors_row['MaxColors'].max()
    else:
        return None

def main():
    st.title("XD Connects Calculator")

    product_price_feed_df = pd.read_csv("https://raw.githubusercontent.com/sunsuzy/xd/main/Xindao.V2.ProductPrices-nl-nl-C26907%20(1).txt", delimiter='\t')
    print_price_feed_df = pd.read_csv("https://raw.githubusercontent.com/sunsuzy/xd/main/Xindao.V2.PrintPrices-nl-nl-C26907%20(1).txt", delimiter='\t')
    print_data_df = pd.read_csv("https://raw.githubusercontent.com/sunsuzy/xd/main/Xindao.V2.PrintData-nl-nl-C26907.txt", delimiter='\t', encoding='ISO-8859-1')

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

        selected_print_technique = print_price_feed_df[print_price_feed_df['PrintCode'] == print_technique[0]].copy()
        selected_print_technique.loc[:, 'NrOfColors'] = pd.to_numeric(selected_print_technique['NrOfColors'], errors='coerce')

        if print_technique[0] in ['Embroidery', 'Embroidery 3D', 'Embroidery badge', 'Hot Stamping', 'Leather badge', 'Printed badge']:
            print_areas = selected_print_technique['PrintArea'].dropna().unique()
            preferred_print_area = st.selectbox('Select preferred print area', options=print_areas, index=0)
            selected_print_technique = selected_print_technique[selected_print_technique['PrintArea'] == preferred_print_area]

        max_colors = get_max_colors_for_print_code(print_technique[0], item_code, print_data_df)

        if max_colors is not None:
            available_colors = [str(i) for i in range(1, max_colors + 1)]
        else:
            available_colors = selected_print_technique['NrOfColors'].dropna().unique()
            available_colors = [str(int(color)) if not pd.isna(color) else 'None' for color in available_colors]

        print_colors = st.selectbox('Enter the number of print colors', options=available_colors, index=0)


        quantity = st.number_input('Enter quantity', min_value=1)

        product_tier = get_product_price_tier(selected_product, quantity)
        applicable_nett_price = get_product_tier_price(selected_product, product_tier)
        total_product_cost = quantity * applicable_nett_price

        if print_colors is None:
            number_of_colors = None
        else:
            number_of_colors = int(float(print_colors))

        selected_print = selected_print_technique[(selected_print_technique['NrOfColors'].isna()) | 
                                                  (selected_print_technique['NrOfColors'] == number_of_colors)]

        if selected_print['NrOfColors'].isna().all():
            if selected_print['PrintArea'].isna().all():
                selected_print = selected_print.iloc[0:1]
            else:
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
