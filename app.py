import pandas as pd
import streamlit as st
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import math
import re
import geopy.distance
from fuzzywuzzy import fuzz
import geocoder
import datetime
from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events
from pyzipcode import ZipCodeDatabase
from geopy.geocoders import Nominatim
geolocator = Nominatim(user_agent="MNCRAFTBREWINGAPP")

## Data
# locations = pd.read_csv(
#     '/mnt/c/rscripts/Brewery App/bar_addresses_with_location.csv')

sheet_id = '1-1KBcSS_BkUMkYOC4cI9d7K4EXK31b8HrcnLHCrG1NQ'
sheet_name = 'Brewery_List'
url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}'
data = pd.read_csv(url)
locations = pd.read_csv(
    f'https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=bar_addresses_with_location')
ranking = pd.read_csv(f'https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Rankings')

data = data.join(ranking.set_index('Brewery Name'), on='Brewery Name', rsuffix = '_right')

def match_brewery(brewery):
    options = [fuzz.token_set_ratio(brewery, opt)
               for opt in locations.name.tolist()]
    best_match = locations.name.tolist()[options.index(max(options))]
    if max(options) < 90:
        return None
    else:
        return best_match

data['place'] = data['Brewery Name'].apply(match_brewery)

all_breweries = pd.merge(locations, data, left_on='name', right_on='place', how='left')

all_breweries['visited'] = [pd.notna(i) for i in all_breweries['Rank']]
all_breweries['craftnotes'] = [pd.notna(i) for i in all_breweries['CraftNotes']]

def visit_color(visited, craftnotes):
  if visited:
    return "Visited!"
  elif craftnotes and not visited:
    return 'In Craft Notes'
  else:
    return 'Not Visited'

all_breweries['color'] = all_breweries.apply(
    lambda x: visit_color(x['visited'], x['craftnotes']), axis=1)

all_breweries['lon'], all_breweries['lat'] = zip(
    *all_breweries['location'].apply(lambda x: tuple(map(float, x.split(',')))))

all_breweries['coords'] = all_breweries.apply(lambda x: (x['lat'], x['lon']), axis=1)


def get_zipcode(address):
  try:
    return re.findall(r'\d{5}$', address)[0]
  except:
    return None

all_breweries['zipcode'] = all_breweries['address'].apply(get_zipcode)

def ordinal(b):
  if pd.notnull(b):
    n = int(b)
    return "%d%s" % (
        n, "tsnrhtdd"[(n//10 % 10 != 1)*(n % 10 < 4)*n % 10::4])
  else:
    return 'Not Ranked'

all_breweries['RankingOrder'] = all_breweries['Rank'].apply(ordinal)

all_breweries['Scores'] = all_breweries.Scores.fillna(0)

missing_locations = data[pd.isnull(data['place'])]

left_to_visit = all_breweries[~all_breweries['visited'] & all_breweries['craftnotes']]

## App

st.markdown("""<style>
.css-fk4es0 {
    position: absolute;
    top: 0px;
    right: 0px;
    left: 0px;
    height: 0.5rem;
    background-image: linear-gradient(
90deg, rgb(220, 53, 34), rgb(234, 130, 119));
    z-index: 1000020;
}
</style>""", unsafe_allow_html=True)

with st.container():
  st.title("Minnesota Craft Beer Map")
  st.markdown(f"""The State of Minnesota is home to {all_breweries.shape[0]} breweries, 
  creating a rich culture of beer. As part of this, the Minnesota Craft Brewer's Guild created
  'Craft Notes', a passport to the craft beer scene. This app is a map of breweries, complete with 
  rankings, notes, and a search bar.""")

  c1, c2, c3 = st.columns([1, 1, 1])
  with c1:
    st.metric('Breweries Visited', f"{int(all_breweries['visited'].sum())} of {all_breweries.shape[0]}")
  with c2:
    st.metric('% of state Visited', f"{round(all_breweries['visited'].sum() / all_breweries.shape[0] * 100, 2)}%")
  with c3:
    st.metric('Craft Notes %', f"{round(100*all_breweries[all_breweries.visited]['craftnotes'].sum()/67, 2)}%")

  page = st.sidebar.radio('Select a page', 
  ['Map', 'Rankings', 'Find Near Me', 'Find by Zip or City', 'Leave a Review'])

if page == 'Map':
  st.subheader('Map')
  st.markdown(f"""The map below shows breweries in the state of Minnesota. 
  Click on a brewery to see more information.
  """)
  fig = px.scatter_mapbox(all_breweries, lat='lat', lon='lon', color='color',
                          hover_name='name', hover_data=['address', 'Scores', 'RankingOrder', "name"], 
                          height = 750, width= 650, zoom=5.5,
                          color_discrete_sequence=['#2980B9', '#45BF55', '#DC3522'])
  fig.update_layout(mapbox_style="dark",
                    mapbox_accesstoken='pk.eyJ1IjoiYW5kcmV3YXJnZXJvcyIsImEiOiJja3k4d2wwMXkwMHAxMm9wODhvd3lnMWRlIn0.MYsPjVtPLaqVAHRIqcv_XQ',
                    legend = dict(orientation="h", yanchor="bottom", y=-0.05, xanchor="right", x=1, title="Brewery Status"),
                    font = dict(size=14, family = "Open Sans"))
  fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 1})
  fig.update_layout(mapbox=dict(center=go.layout.mapbox.Center(
      lat=46.72,
      lon=-93.985)))
  fig.update_traces(marker=dict(size=10, opacity=0.75),
                    hovertemplate=('<br><b>%{customdata[3]}</b><br>' +
                                   '<br>%{customdata[0]}' +
                                   '<br><b>Score</b>: %{customdata[1]}' +
                                   '<br><b>Rank</b>: %{customdata[2]}'))
  st.plotly_chart(fig)
  
  st.header("Want to learn more?")
  st.write("Use the Search bar to find a brewery by name.")

  search = st.text_input("Search for a brewery")

  def format_comments(comments):
    all_comments = comments.split(',')
    all_comments = [f"- {i.strip().title()}" for i in all_comments]
    return "\n".join(all_comments)

  def make_card(brewery):
    ctr = st.container()
    ctr.header(brewery[1])
    ctr.write(f"*{brewery[2]}*")
    ctr.subheader(
        f"**Rank: {brewery[4]} | Score: {brewery[3]} | {int(brewery[5])} Options Available**")
    comms, food = st.columns([1, 1])
    comms.write("**Comments**")
    comms.write(format_comments(brewery[10]))
    food.write("**Food**")
    food.write(format_comments(brewery[11]))
    c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1])
    c1.metric('Atmosphere', brewery[6])
    c2.metric("Andrew's Selection", brewery[7])
    c3.metric("Olivia's Selection", brewery[8])
    c4.metric("Glassware", brewery[9])
    c5.metric("Overall", brewery[3])
    return(ctr)

  if search:
    search_results = all_breweries[all_breweries['name'].str.contains(search, case=False) & all_breweries['visited']]
    if search_results.shape[0] > 0:
      search_res = search_results[['name', 'address', 'Scores', 
      'RankingOrder', '# of Taps', 'Atmosphere ', 'Selection Andrew', 
      'Selection Olivia', 'Glassware', 'Comments', 'Food']]
      for row in search_res.itertuples():
        make_card(row)
        st.write("---")
    else:
      st.subheader("No results found. We probably haven't visited that brewery yet. Check back soon!")

elif page == "Rankings":

  st.header("Rankings")
  st.markdown(f"""The rankings below show the top breweries in the state of Minnesota,
  based on our scores. You might not agree with these rankings, but they are the best 
  we've got, and an excuse for you to make your own.""")

  rank_choice = st.sidebar.radio('Rankings By:', ['Overall', 'Atmosphere ', 'Glassware', "Selection Andrew", 'Selection Olivia', "New: Algorithm"])

  rankings = all_breweries[all_breweries['visited']][['name', 'address', 'Scores',
                                                      'RankingOrder', 'Atmosphere ', 
                                                      'Glassware', "Selection Andrew",
                                                      'Selection Olivia']]

  limit_rank = st.sidebar.slider(
      'Limit to:', min_value=1, max_value=rankings.shape[0], value=10)

  if rank_choice == "Overall":                                                    
    rankings2 = rankings.sort_values(by='Scores', ascending=False).reset_index(drop=True)
  elif rank_choice == "New: Algorithm":
    rankings = all_breweries[all_breweries['visited']][['name', 'Atmosphere ',
                                                        'Glassware', "Selection Andrew",
                                                        'Selection Olivia']]
    rankings_norm = rankings.set_index('name').apply(
        lambda x: (x - x.min()) / (x.max() - x.min()))
    rankings_norm = rankings_norm.apply(lambda x: x.sum()/len(x), axis=1).reset_index()
    rankings2 = rankings.copy()
    rankings_norm = rankings_norm.rename(columns={0: 'Algorithm'})
    rankings2 = rankings2.set_index('name').join(
    rankings_norm.set_index('name'), on='name')
    rankings2 = rankings2.sort_values(by='Algorithm', ascending=False).reset_index()
  else:
    rankings2 = rankings.sort_values(by=rank_choice, ascending=False).reset_index(drop=True)

  st.dataframe(rankings2.head(limit_rank), height=500)

elif page == 'Find Near Me':

  st.header("Find a Place Near Me")
  st.markdown(f"""The search bar below allows you to find a brewery near you. 
  Use the Radio buttons to select the filters you'd like. Note, to refresh your location, click the button below.""")

  new_breweries = st.sidebar.checkbox("Show only breweries we haven't visited", value=False)
  inbook = st.sidebar.checkbox("Show only breweries in Craft Notes", value=False)
  limit = st.sidebar.slider("Limit results to", 1, 50, value=5)

  # loc_button = st.button("Find a Brewery")

  def distance(p1, p2):
    return geopy.distance.distance(p1, p2).miles

  def make_card(brewery):
    ctr = st.container()
    ctr.subheader(brewery[1])
    ctr.write(f"*{brewery[2]}*")
    ctr.write(f"Approximate Distance: {round(brewery[3], 2)} miles")
    return(ctr)

  loc_button = Button(label="Find a Brewery Near Me")
  loc_button.js_on_event("button_click", CustomJS(code="""
      navigator.geolocation.getCurrentPosition(
          (loc) => {
              document.dispatchEvent(new CustomEvent("GET_LOCATION", {detail: {lat: loc.coords.latitude, lon: loc.coords.longitude}}))
          }
      )
      """))
  result = streamlit_bokeh_events(
      loc_button,
      events="GET_LOCATION",
      key="get_location",
      refresh_on_update=False,
      override_height=75,
      debounce_time=0)

  if loc_button:
    if "GET_LOCATION" in result:
      me = result.get("GET_LOCATION")
      st.write(f'We estimate your location as {result.get("GET_LOCATION")["lat"]}, {result.get("GET_LOCATION")["lon"]}')
      me = (me['lat'], me['lon'])

      all_breweries['distance'] = all_breweries.apply(lambda x: distance(me, (x['lat'], x['lon'])), axis=1)
      
      if new_breweries & inbook:
        all_breweries3 = all_breweries[~all_breweries['visited'] & all_breweries['craftnotes']]
      elif new_breweries:
        all_breweries3 = all_breweries[~all_breweries['visited']]
      elif inbook:
        all_breweries3 = all_breweries[all_breweries['craftnotes']]
      else:
        all_breweries3 = all_breweries
      
      all_breweries3 = all_breweries3.sort_values(by='distance', ascending=True).reset_index(drop=True).head(limit)

      for row in all_breweries3[['name', 'address', 'distance']].itertuples():
        make_card(row)
        st.write("---")
  else:
    st.write("We can't find your location. Please enable location services in your browser.")

elif page == 'Find by Zip or City':

  choice = st.sidebar.radio("Search by:", ['Zip Code', 'City'])
  new_breweries = st.sidebar.checkbox(
      "Show only breweries we haven't visited", value=False)
  inbook = st.sidebar.checkbox(
      "Show only breweries in Craft Notes", value=False)
  limit = st.sidebar.slider("Limit results to", 1, 50, value=5)

  def distance(p1, p2):
    return geopy.distance.distance(p1, p2).miles

  def make_card(brewery):
    ctr = st.container()
    ctr.subheader(brewery[1])
    ctr.write(f"*{re.sub(r'[^A-Za-z0-9 ]+', '', brewery[2])}*")
    ctr.write(f"Approximate Distance: {round(brewery[3], 2)} miles")
    return(ctr)

  st.header("Find Breweries by {choice}".format(choice=choice))

  if new_breweries & inbook:
    all_breweries3 = all_breweries[~all_breweries['visited'] & all_breweries['craftnotes']]
  elif new_breweries:
    all_breweries3 = all_breweries[~all_breweries['visited']]
  elif inbook:
    all_breweries3 = all_breweries[all_breweries['craftnotes']]
  else:
    all_breweries3 = all_breweries

  if choice == 'Zip Code':
    zcdb = ZipCodeDatabase()
    zip_code = st.sidebar.text_input("Zip Code", value="55101", max_chars=5)
    place = zcdb.get(zip_code)
    place = (place.latitude, place.longitude)

  elif choice == 'City':
    city = st.sidebar.text_input("City", value="St. Paul")
    city = f'{city}, Minnesota'
    place = geolocator.geocode(city)
    place = (place.latitude, place.longitude)
  
  if place:
    all_breweries3['distance'] = all_breweries3.apply(lambda x: distance(place, (x['lat'], x['lon'])), axis=1)
    all_breweries3 = all_breweries3.sort_values(by='distance', ascending=True).reset_index(drop=True).head(limit)

    for row in all_breweries3[['name', 'address', 'distance']].itertuples():
      make_card(row)
      st.write("---")
  
elif page == "Leave a Review":
  st.header("Leave a Review")
  brewery = st.selectbox("Select a Brewery", all_breweries['name'])
  date_visited = st.date_input("Date Visited", value=datetime.date.today())
  taps = st.number_input("Number of Taps", value=1, min_value=1, max_value=100)

  order = st.text_input("What did you order? Enter multiple drinks seperated with commas",
   value="")

  col1, col2 = st.columns(2)

  with col1:
    st.subheader("Atmosphere")
    st.write('''Please rate the atmosphere from 1-10. 
    This includes the overall aesthetics of the brewery, your experience ordering, 
    and the overall overall experience.''')
    atmosphere = st.slider("Atmosphere", 1.0, 10.0, value=5.0, step=0.25)
  with col2:
    st.subheader("Glassware")
    st.write('''Please rate the glassware from 1-10.
    To us, a brewery with a high glassware of 5 score has multiple options for
    glasses, fun shapes, and a cool on glass printing/etching.''')
    glassware = st.slider("Glassware", 1.0, 10.0, value=5.0, step=0.25)
  with col1:
    st.subheader("Beer Selection")
    st.write('''Please rate the selection of beer from 1-10. Selection includes both how
    many beers you *would have tried* and the *quality of the beer you tried*. Note: Only
    include beer in this rating-- No Seltzers, Ciders, etc.''')
    beer = st.slider("Beer Selection", 1.0, 10.0, value=5.0, step=0.25)
  with col2:
    st.subheader("Non-Beer Selection")
    st.write('''Please rate the selection of the seltzers, ciders, cocktails and other beverages from 1-10. 
    Selection includes both how many drinks you *would have tried* and the *quality of the drink(s) you tried*.
    Please do not include beer in this rating.''')
    nonbeer = st.slider("Non-Beer Selection", 1.0, 10.0, value=5.0, step=0.25)

  email = st.text_input("Enter your Email to Submit", value="")
  if st.button("Submit"):
    if email:
      if re.match(r'[^@]+@[^@]+\.[^@]+', email):
        user_data = {
          'email': email,
          'brewery': brewery,
          'date_visited': date_visited,
          'taps': taps,
          'order': order,
          'atmosphere': atmosphere,
          'beer': beer,
          'nonbeer': nonbeer,
          'glassware': glassware
        }
        st.success("Thank you for your review!")
      else:
        st.write("Please enter a valid email address.")
    else:
      st.write("Please enter an email address.")
