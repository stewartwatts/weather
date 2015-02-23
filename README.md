NOAA Data
=========

Play with NOAA's Heating Degree Day and Cooling Degree Day data.  
Required packages: pandas, matplotlib, dateutil  
Recommended packages: seaborn

Use
========

First, build a csv, "degree_days.csv", from NOAA's data.  If the csv already exists, calling the script just updates the file with the most recent data.
```
$ python degree_days.py
```

Then load, reformat, and plot the data for a region and type of season.
```python
from degree_days import load_file, plot_region_seasons
df = load_file()

# plot a season by census region or state, highlighting the last couple years
plot_region_season(df, "USA", "HDD", ["2013", "2014"], "USA.png")
plot_region_season(df, "NY", "HDD", ["2013", "2014"], "NY.png")
```

- The 2014 "cooling season" spans 2014-01-01 to 2014-12-31.  
- The 2014 "heating season" spans 2014-07-01 to 2015-06-30.  
- Larger values on the charts means a colder "heating season" (winter) or a warmer "cooling season" (summer).  
- Census regions: "NEW ENGLAND", "MIDDLE ATLANTIC", "E N CENTRAL", "W N CENTRAL", "SOUTH ATLANTIC", "E S CENTRAL", "W S CENTRAL", "MOUNTAIN", "PACIFIC", "USA", or state abbreviations, like "NY".

![alt tag](https://raw.github.com/stewartwatts/weather/blob/master/USA.png?raw=true)
