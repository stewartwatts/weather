"""
Parse NOAA population-weighted HDD and CDD text data to pandas DataFrame
"""
import os
import pandas as pd
import datetime as dt
from time import sleep
try:
    import seaborn as sns
except:
    pass
import matplotlib.pyplot as plt
from dateutil.parser import parse


OUT_FILENAME = "degree_days.csv"   # a csv in the current directory
START_YEAR = 1981                  # first year NOAA has data
url_fmt = "ftp://ftp.cpc.ncep.noaa.gov/htdocs/degree_days/weighted/daily_data/%s/Population.%s.txt"
states_fmt = "ftp://ftp.cpc.ncep.noaa.gov/htdocs/degree_days/weighted/daily_data/%s/StatesCONUS.%s.txt" 
# int -> census regions for parsing the data
key_map = {
    "1": "NEW ENGLAND", "2": "MIDDLE ATLANTIC", "3": "E N CENTRAL",
    "4": "W N CENTRAL", "5": "SOUTH ATLANTIC", "6": "E S CENTRAL",
    "7": "W S CENTRAL", "8": "MOUNTAIN", "9": "PACIFIC",
    "CONUS": "USA", "Region": "Date"
    # implicitly states map to themselves: "NY" -> "NY"
}

headers = [("Connection", "Keep-Alive")]
def hit_url(url):
    req = urllib2.Request(url)
    for header in headers:
        req.add_header(*header)
    resp = urllib2.urlopen(req)
    return resp

# ----- scraping logic ----- #
def data_from_year(year):
    """
    Get CDD and HDD data from NOAA for a given year, and parse into a DataFrame
    `year`: string
    """
    print "scraping < %s >" % year
    def process_line(line):
        data = line.split("|")
        f = parse if data[0] == "Region" else float
        return (key_map.get(data[0], data[0]), map(f, data[1:]))

    cool_txt = hit_url(url_fmt % (year, "Cooling")).read().strip().split("\n")
    sleep(2.)
    heat_txt = hit_url(url_fmt % (year, "Heating")).read().strip().split("\n")
    sleep(2.)
    states_cool_txt = hit_url(states_fmt % (year, "Cooling")).read().strip().split("\n")
    sleep(2.)
    states_heat_txt = hit_url(states_fmt % (year, "Heating")).read().strip().split("\n")
    sleep(2.)

    # isolate data lines
    cool_txt = filter(lambda line: "|" in line, cool_txt)
    heat_txt = filter(lambda line: "|" in line, heat_txt)
    states_cool_txt = filter(lambda line: "|" in line, states_cool_txt)
    states_heat_txt = filter(lambda line: "|" in line, states_heat_txt)

    # lines -> dataframe with columns for each region
    cool = pd.DataFrame(dict(map(process_line, cool_txt)))
    heat = pd.DataFrame(dict(map(process_line, heat_txt)))
    states_cool = pd.DataFrame(dict(map(process_line, states_cool_txt)))
    states_heat = pd.DataFrame(dict(map(process_line, states_heat_txt)))

    # combine with MultiIndex on Heating/Cooling
    cool.set_index("Date", inplace=True)
    heat.set_index("Date", inplace=True)
    states_cool.set_index("Date", inplace=True)
    states_heat.set_index("Date", inplace=True)
    cool = pd.concat([cool, states_cool], axis=1)
    heat = pd.concat([heat, states_heat], axis=1)
    df = pd.concat([cool, heat], axis=1, keys=["CDD", "HDD"])
    return df

def load_file(filepath=OUT_FILENAME):
    # read an existing degree day file from disk with correct formatting
    return pd.read_csv(filepath, index_col=0, header=[0, 1], parse_dates=True)

def update_degree_days(filepath=OUT_FILENAME):
    """
    Main function to build or update a CDD/HDD data file
    """
    try: 
        existing_df = load_file(filepath)
    except:
        existing_df = None

    start_year = existing_df.index[-1].year if existing_df is not None else START_YEAR
    end_year = dt.date.today().year
    years = range(start_year, end_year + 1)
    new_df = pd.concat([data_from_year(year) for year in map(str, years)], axis=0)
    full_df = new_df.combine_first(existing_df) if existing_df is not None else new_df
    full_df.sort_index(inplace=True)
    print "writing < %s >" % OUT_FILENAME
    print "\tdates: %s .. %s" % (full_df.index[0].strftime("%Y-%m-%d"), full_df.index[-1].strftime("%Y-%m-%d"))
    full_df.to_csv(OUT_FILENAME)

# ----- data logic ----- #
def get_region_seasons(df, region): 
    """
    reformat the DataFrame with all data to contain all seasons for a given region
    Cooling seasons (summer): Jan-01 to Jan-01
    Heating seasons (winter): Jul-01 to Jul-01
    """
    sd, ed = df.index[0], df.index[-1]
    cool = df[("CDD", region)]
    heat = df[("HDD", region)]

    # series subsets corresponding to each yearly season
    cools, heats = [], []
    for yr in range(sd.year, ed.year + 1):
        ser = cool.loc[(cool.index >= pd.Timestamp(dt.date(yr, 1, 1))) & (cool.index < pd.Timestamp(dt.date(yr + 1, 1, 1)))]
        ser.reset_index(drop=True, inplace=True)
        ser.name = str(yr)
        cools.append(ser)

        ser = heat.loc[(heat.index >= pd.Timestamp(dt.date(yr, 7, 1))) & (heat.index < pd.Timestamp(dt.date(yr + 1, 7, 1)))]
        ser.reset_index(drop=True, inplace=True)
        ser.name = str(yr)
        heats.append(ser)

    cools = pd.concat(cools, axis=1).iloc[:365, :]
    cool_cum = cools.cumsum()
    cools["mean"] = cools.mean(axis=1)
    cool_cum["mean"] = cool_cum.mean(axis=1)
    heats = pd.concat(heats, axis=1).iloc[:365, :]
    heat_cum = heats.cumsum()
    heats["mean"] = heats.mean(axis=1)
    heat_cum["mean"] = heat_cum.mean(axis=1)

    daily = pd.concat([cools, heats], axis=1, keys=["CDD", "HDD"])
    cumulative = pd.concat([cool_cum, heat_cum], axis=1, keys=["CDD", "HDD"])
    return daily, cumulative 

def plot_region_seasons(all_df, region, season, years, fn=None):
    """
    `all_df`: all data DataFrame
    `season`: name of the region in all caps
    `season`: "CDD" or "HDD"
    `year`: list of years as YYYY str; the 2014 heating season starts in July 2014 and wraps into 2015

    Plots:
    1. All seasons of this type, with mean and `years` highlighted
    2. All seasons with mean subtracted off, with mean and `years` highlighted
    """
    if type(years) == str:
        years = [years]
    assert season in ["CDD", "HDD"], "plot_region_season(): `season` <%s> must be in: \n\t['CDD', 'HDD']" % season
    
    daily, cumulative = get_region_seasons(all_df, region)
    start = dt.date(2014, 1 if season == "CDD" else 7, 1)
    date_idx = [(start + dt.timedelta(days=i)).strftime("%b%d") for i in range(len(cumulative))]
    cumulative.index = date_idx
    # first 100 / last 60 days of each season has pretty much no activity; discard them 
    df = cumulative[season].iloc[100:-55, :]
    fig, axs = plt.subplots(2, 1, figsize=(10, 10))
    
    # 1
    df.plot(ax=axs[0], alpha=0.3, lw=0.8, title="%s Cumulative %s" % (region, season))
    axs[0].plot(df["mean"], color="k", lw=2, label="mean")
    for year in years: 
        axs[0].plot(df[year], lw=2, label=year)
    handles, labels = axs[0].get_legend_handles_labels()
    n = len(years) + 1
    axs[0].legend(handles[-n:], labels[-n:], loc="best")

    # 2
    df2 = df.sub(df["mean"], axis=0)
    df2.plot(ax=axs[1], alpha=0.3, lw=0.8, title="%s Cumulative %s Vs Avg" % (region, season))
    axs[1].plot(df2["mean"], color="k", lw=2, label="mean")
    for year in years:
        axs[1].plot(df2[year], lw=2, label=year)
    handles, labels = axs[1].get_legend_handles_labels()
    n = len(years) + 1
    axs[1].legend(handles[-n:], labels[-n:], loc="best")

    if fn:
        fig.savefig(fn, bbox_inches="tight")
    else:
        fig.show()


if __name__ == "__main__":
    update_degree_days()