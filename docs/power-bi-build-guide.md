# Build the tempo report in Power BI

This is a study build for Exam PL-300 (Microsoft Power BI Data Analyst), using the skill outline published for exams as of April 20, 2026. The outline and the weights below are from the [PL-300 study guide](https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/pl-300). Build the report yourself. This repo does not contain a `.pbix`.

You need Power BI Desktop. Publishing and sharing need a Power BI license or a Fabric capacity. Desktop alone is enough for the model, the measures, and the pages.

The question the report should answer is the same one in the README: how the stored tempo of the African-scene cohort compares with the hip-hop genre proxy, before and after the half-time fold. If a card disagrees with the README, the card is wrong.

## Skill map

| Study-guide area | Weight | What you practice here |
| --- | --- | --- |
| Prepare the data | 25–30% | Import the CSVs, set types, profile columns, a parameter, a reference query, fact and dimension tables that stay in a star |
| Model the data | 25–30% | Relationships, filter direction, a role-playing tempo band, DAX measures, `CALCULATE` and `REMOVEFILTERS`, a measure that must not sum popularity |
| Visualize and analyze the data | 25–30% | Cards, a band chart, a scatter with a reference line, slicers, bookmarks, a tooltip page, drillthrough, mobile layout, accessibility |
| Manage and secure Power BI | 15–20% | Workspace, app, refresh and gateway choices, a practice row-level security role, workspace roles, sensitivity |

## Files to load

Load these six files from `powerbi/star/` and nothing else. Do not load `analysis_tracks.csv` beside them. That file is already split into the star.

| File | Table | Rows | Role |
| --- | --- | --- | --- |
| `fact_track.csv` | `fact_track` | 907 | One track in one cohort in one snapshot. Measures live on this grain. |
| `dim_snapshot.csv` | `dim_snapshot` | 2 | Spotify tracks dataset, or the current charts |
| `dim_cohort.csv` | `dim_cohort` | 4 | Two comparison arms, each defined once for the dataset and once for the charts |
| `dim_artist.csv` | `dim_artist` | one row per primary artist | Country and scene from the dataset lookup. Blank country is correct when the artist is only on a chart. |
| `dim_track.csv` | `dim_track` | 907 | Track title, credit string, album, duration |
| `dim_tempo_band.csv` | `dim_tempo_band` | 6 | Tempo bands. `bpm_max_exclusive` of 9999 means "160 and above", not a real cap. |

`powerbi/measures.dax` is the measure script. `powerbi/theme.json` is the report theme.

## 1. Prepare the data

### Get or connect to data

1. Home, Get data, Text/CSV. Load each file in the table above. Choose Import when Desktop asks. Load, do not only create a connection you forget to close and apply.
2. Why Import: the source is a local CSV. DirectQuery does not apply to these files. DirectLake applies to Delta tables in a Fabric lakehouse, which this project is not. Naming the wrong mode is a scored distinction. So is knowing that a shared semantic model is the right source when one already exists. One does not exist here. You are building the semantic model.
3. Set the file origin to UTF-8 if titles look garbled. Names such as Cesária Evora and Côte d'Ivoire are in the artist table and must survive the load.

Parameter exercise, after the five queries load and you have confirmed the row counts:

1. Home, Manage parameters, New. Name it `DataFolder`. Type Text. Current value: the full path of `powerbi/star` with no trailing slash.
2. In Advanced Editor for `fact_track`, replace the hard-coded path with `DataFolder & "\fact_track.csv"` on Windows or `DataFolder & "/fact_track.csv"` on macOS.
3. Repeat for the other five queries, including `dim_snapshot`. If a query breaks, paste the original path back. The parameter is the exam skill. A working model matters more than a broken one.
4. Privacy levels: these files are the same folder. If a later merge warns about privacy, set every query to Organizational, or every query to Public. Do not mix levels.

### Profile and clean the data

1. In Power Query, View, turn on Column quality, Column distribution, and Column profile.
2. On `fact_track`, `tempo_raw` and `tempo_corrected` should show no errors and no empty values. Popularity is blank on the current-chart rows. Leave those blanks. The chart did not provide Spotify's 0–100 index, and a zero would mean a real score. `chart_market` is the country of the chart. It is not the artist's origin, and it is not `dim_artist[country]`. `deezer_bpm` is 0 on the measured chart rows because the public track response returned 0. `is_top100` should contain only 0 and 1.
3. On `dim_artist`, country is blank for hip-hop primary artists. Leave it blank. Do not fill it with "United States". The hip-hop cohort is a genre proxy, and a blank is the honest value.
4. There is nothing to impute. Do not replace tempos, and do not drop the three tracks under 80 BPM in the African eligible set just because the top 100 has none. The `is_top100` filter handles the headline set.

### Transform and load the data

Set these types in Power Query so the step is visible in Applied Steps, not only in the model view.

| Columns | Type |
| --- | --- |
| Every column ending in `_key`, plus `sort_order`, `popularity`, `popularity_rank`, `is_top100`, `explicit`, `octave_shifts`, `octave_shifted`, `time_signature`, `duration_ms`, `bpm_min`, `bpm_max_exclusive` | Whole number |
| `tempo_raw`, `tempo_corrected`, `tempo_corrected_alt`, `danceability`, `energy`, `valence`, `speechiness`, `acousticness`, `loudness` | Decimal number |
| Names, titles, `cohort_id`, `band_label`, `octave_direction`, `definition`, `scene`, `country`, `region` | Text |

Role-playing dimension:

1. Right-click `dim_tempo_band`, Reference. Do not choose Duplicate. A reference stays tied to the source query. A duplicate copies the steps and will drift if you change a band label later.
2. Rename the reference to `dim_tempo_band_corrected`.
3. Leave the columns as they are. The two tables are the same six bands. They play different roles: one filters `raw_band_key`, the other filters `corrected_band_key`.

The fact and the dimensions are already separated. Do not merge them back into one wide table. The study guide lists "create fact tables and dimension tables" and "merge and append queries" because both come up. Here the merge would undo the star. If you want the muscle memory, reference `fact_track`, merge `dim_cohort` onto `cohort_key` as a left outer join, confirm `cohort_name` appears, then delete that practice query and leave its load disabled. The relationship in the next section does the same job without storing `cohort_name` twice.

`track_key` is the surrogate key. `track_id` is the Spotify id. Relate tables on the surrogate. Keep `track_id` on `dim_track` so a drillthrough page can show it.

Close and apply.

## 2. Model the data

### Design and implement a data model

In Model view, create these relationships. Cardinality is many on `fact_track` to one on the dimension. Cross-filter direction is single, from the dimension to the fact. Do not turn on bi-directional filters. This model does not need them, and they make filter context harder to explain.

| From | To |
| --- | --- |
| `dim_snapshot[snapshot_key]` | `fact_track[snapshot_key]` |
| `dim_cohort[cohort_key]` | `fact_track[cohort_key]` |
| `dim_artist[artist_key]` | `fact_track[artist_key]` |
| `dim_track[track_key]` | `fact_track[track_key]` |
| `dim_tempo_band[band_key]` | `fact_track[raw_band_key]` |
| `dim_tempo_band_corrected[band_key]` | `fact_track[corrected_band_key]` |

If Desktop offers one-to-one on `track_key`, that matches the data (one fact row per track). Prefer a single filter direction from `dim_track` to `fact_track`. If one-to-one forces both directions, set the relationship to one-to-many from `dim_track` instead. The "one" side is still the dimension.

Do not also draw a relationship from `corrected_band_key` to the original `dim_tempo_band`. Two relationships between the same two tables cannot both be active. The reference table is how this model does the role-playing dimension the exam asks for.

Then:

1. Hide every key column from report view. Right-click the column, Hide. Hidden columns still work in relationships and in DAX.
2. On both band tables, select `band_label`, Column tools, Sort by column, `sort_order`. If you skip this, "160 and above" sorts before "80-99".
3. Mark `dim_cohort[definition]` and the long text columns you will not put on a visual as hidden if the field list feels crowded. Do not delete them.
4. In the fact table properties, confirm the grain to yourself: one row per track per cohort, 761 rows before any report filter.

There is no date column. Do not add a date table. A `CALENDAR` table with invented dates would make time intelligence return numbers that are not about this music. That is the wrong answer to "create a common date table". The study note, which you should not load into this model, is:

```dax
Date =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2018, 1, 1 ), DATE ( 2024, 12, 31 ) ),
    "Year", YEAR ( [Date] ),
    "Month", FORMAT ( [Date], "MMM" ),
    "Month number", MONTH ( [Date] )
)
```

You would mark that table as a date table only when a real fact column held a date. Forecasting is the same story. It needs a continuous date axis. This report does not have one, so the Analytics pane forecast is the wrong tool. Say that if an item stem offers it.

### Create model calculations by using DAX

On `fact_track`, New measure, and paste one measure at a time from `powerbi/measures.dax`. The `--` lines are comments. DAX accepts them. Paste them or skip them. Do not paste two measure definitions into one measure.

After `dim_tempo_band_corrected` exists, add this measure. It is not in the file because that table does not exist until you create the reference.

```dax
Corrected Band Share =
DIVIDE (
    [Track Count],
    CALCULATE ( [Track Count], ALL ( dim_tempo_band_corrected ) )
)
```

Format:

| Measure | Format |
| --- | --- |
| `Average Tempo Raw`, `Median Tempo Raw`, `Average Tempo Corrected`, `Median Tempo Corrected`, both gap measures, `Popularity Weighted Tempo` | Decimal number, 1 decimal |
| `Average Popularity`, `Max Popularity`, `Track Count` | Whole number, or 1 decimal for the two popularity averages |
| `Octave Shift Share`, `Halved Share`, `Raw Band Share`, `Corrected Band Share` | Percentage, 1 decimal |

Read the measures before you use them.

- `Track Count` is `COUNTROWS`, not `COUNT` of a column. At this grain they match. `COUNTROWS` is the one that still means "tracks" if you later add a column.
- `Average Popularity` and `Max Popularity` are the legal aggregations. Popularity is a 0–100 index. `SUM` of it is not a total of anything. The exam calls a closing-balance pattern semi-additive. This index is not a balance. `Max Popularity` answers "what is the highest index in this slice". `Average Popularity` answers "what is typical". Use the average on the cards.
- `Median Tempo Raw Gap` uses `CALCULATE` and `REMOVEFILTERS ( dim_cohort )`. A cohort slicer filters `cohort_name`. The measure then sets `cohort_id`. Those are different columns, so without `REMOVEFILTERS` the slicer and the measure would both apply and the other cohort would go blank. `REMOVEFILTERS` clears the slicer. The explicit `cohort_id` filter puts one cohort back. The `is_top100` filter is not cleared, so the gap stays on the headline set.
- `Raw Band Share` uses `ALL ( dim_tempo_band )` so the denominator ignores the band on the axis and still respects the cohort slicer. That is percent of cohort, not percent of the whole database.
- `Popularity Weighted Tempo` is a weighted average. The `DIVIDE` guards an empty slice.

Calculated column versus measure: a calculated column is stored and evaluated row by row when the model refreshes. A measure is evaluated in filter context when a visual asks. Tempo averages belong in measures. You do not need a calculated column for "fast versus not". `raw_band_key` already does that, and a column would repeat it.

Calculation groups are on the study guide. This Desktop build may or may not show them in Model view. If it does, an optional group named Tempo Choice with two items, Raw and Corrected, can switch a selected tempo measure. If it does not, stop. The two measures you already created are the right tool. Do not install an outside modeling tool just to tick the box.

### Optimize model performance

The model is small. Do the exam motions anyway.

1. View, Performance Analyzer, start recording, change the cohort slicer, stop. Open the slowest visual. On this model the times will be tiny. You are practicing where to look.
2. Confirm you did not import `analysis_tracks.csv` as a sixth table. Extra tables are the usual way a small model gets messy.
3. Do not add a high-cardinality calculated column on the fact. Titles stay on `dim_track`.

## 3. Visualize and analyze the data

View, Themes, Browse for themes, and pick `powerbi/theme.json`. The report background goes dark. Pink is the African cohort and cyan is the hip-hop proxy, the same pairing as the R charts. If a visual stays on a white background, select it and set the background to the theme default.

Build four pages.

### Page: Overview

Page-level filter: `fact_track[is_top100]` is 1. This is the headline set. A page-level filter is the right place. A report-level filter would also hit the Eligible page, which is the one page that must not use it.

Slicers: `dim_snapshot[snapshot_name]` and `dim_cohort[cohort_name]`. Style them as tiles or dropdowns. The snapshot slicer is required. Without it, the two snapshots are pooled and none of the check numbers below will match. `comparison_arm` on `dim_cohort` is `africa` or `hiphop`. The gap measures filter that column, so they follow the snapshot slicer and still compare the two arms inside it.

Visuals:

1. Card, `Track Count`.
2. Card, `Median Tempo Raw`.
3. Card, `Median Tempo Corrected`.
4. Card, `Octave Shift Share`.
5. Card, `Median Tempo Raw Gap`.
6. Card, `Median Tempo Corrected Gap`.
7. Clustered column chart. Axis `dim_tempo_band[band_label]`. Values `Raw Band Share`. Legend `dim_cohort[cohort_name]`. Turn on data labels. This is the distribution. Desktop has no density geom, and the band share is the honest substitute.
8. Clustered column chart. Axis `dim_tempo_band[band_label]`. Values `Average Popularity`. Legend cohort. The bars should be nearly flat inside a cohort, with hip-hop higher at every band.

Title the page with the question, not with "Dashboard".

With the top-100 filter on, and the snapshot slicer set to **Spotify tracks dataset**, check the cards against this table. Read median and average cards with one cohort selected. A median of the pooled rows is not the average of the two medians, and it is not a number this table lists.

| Selection | Measure | Value |
| --- | --- | --- |
| African popular music | Track Count | 100 |
| US hip-hop (genre proxy) | Track Count | 100 |
| Both, Select all | Track Count | 200 |
| African popular music | Median Tempo Raw | 108.0 |
| US hip-hop (genre proxy) | Median Tempo Raw | 112.7 |
| African popular music | Average Tempo Raw | 120.2 |
| US hip-hop (genre proxy) | Average Tempo Raw | 117.0 |
| African popular music | Median Tempo Corrected | 103.9 |
| US hip-hop (genre proxy) | Median Tempo Corrected | 96.0 |
| African popular music | Average Popularity | 63.0 |
| US hip-hop (genre proxy) | Average Popularity | 80.7 |
| Any cohort slicer state | Median Tempo Raw Gap | -4.7 |
| Any cohort slicer state | Median Tempo Corrected Gap | 7.9 |
| African popular music | Octave Shift Share | 16.0% |
| US hip-hop (genre proxy) | Octave Shift Share | 21.0% |

If the gap card changes when you select one cohort, `REMOVEFILTERS ( dim_cohort )` is missing from the measure. If the gap card changes when you change the snapshot, that is the correct behavior. The dataset's corrected gap is about 7.9 BPM. The current-chart corrected gap is 0.0.

Set the snapshot slicer to **Current charts** and check these cards. Track Count is the number of previews with a librosa tempo, not the full chart. Coverage is in the README.

| Selection | Measure | Value |
| --- | --- | --- |
| Nigeria and South Africa Spotify charts | Track Count | 97 |
| Billboard Hot R&B/Hip-Hop Songs | Track Count | 49 |
| Nigeria and South Africa Spotify charts | Median Tempo Raw | 117.5 |
| Billboard Hot R&B/Hip-Hop Songs | Median Tempo Raw | 123.0 |
| Nigeria and South Africa Spotify charts | Median Tempo Corrected | 112.3 |
| Billboard Hot R&B/Hip-Hop Songs | Median Tempo Corrected | 112.3 |
| Either cohort, this snapshot | Median Tempo Raw Gap | -5.6 |
| Either cohort, this snapshot | Median Tempo Corrected Gap | 0.0 |

`Average Popularity` is blank on this snapshot. Do not replace the blank with zero.

### Page: Half-time

Same page-level filter, `is_top100` is 1.

1. Clustered column. Axis `dim_tempo_band_corrected[band_label]`. Values `Corrected Band Share`. Legend cohort. If this visual is empty, the corrected relationship is missing or it points at the raw band table.
2. Scatter. X `tempo_raw`, Y `popularity`, Legend cohort, Values `Track Count` or leave the well as the fact grain. Tooltips: track name from `dim_track`, primary artist, `tempo_corrected`.
3. On the scatter, Analytics pane, add a constant line on the X axis at 140. Name it "Half-time cut". That line is the fold used in the README. Points to the right of it are the tracks the correction halves.
4. A second scatter, or a bookmark of the same visual, with X = `tempo_corrected`, is worth one try. The 200 BPM African tracks should sit near 100 after the fold. The hip-hop points that were past 140 should sit between 70 and 90.

Do not add a forecast line. There is no date.

### Page: Countries

Page-level filters: `is_top100` is 1, and `dim_cohort[cohort_id]` is `africa_popular`.

1. Bar chart. Axis `dim_artist[country]`. Values `Track Count`. Sort descending. Nigeria should be 91. Blank country must not appear on this page. If it does, the cohort filter is off.
2. Bar chart. Axis `dim_artist[country]`. Values `Median Tempo Raw`. Do not draw a strong conclusion from Cape Verde or Côte d'Ivoire. Those bars are one track.
3. Table: `primary_artist`, `track_name`, `popularity`, `tempo_raw`, `tempo_corrected`. This table is the drillthrough target in the next section.

### Page: Eligible set

No `is_top100` filter. Slicer on cohort.

Track Count should read 208 for the African cohort and 553 for hip-hop. Those are the tracks with popularity at least 40, after dedupe, not the top 100. Put a text box on the page that says so, or the page will be read as a second headline.

### Bookmarks, tooltips, drillthrough

Bookmarks and the Selection pane:

1. On Overview, hide the popularity chart in the Selection pane. View, Bookmarks, Add. Name it Raw tempo.
2. Show the popularity chart, hide the band-share chart. Add a bookmark named Popularity. Update the bookmark so it captures data and display.
3. Add two buttons that apply the bookmarks. View, Bookmarks, selected bookmark, the action is applied from the button's Action property.

Tooltip page:

1. Add a page named Tooltip. Page information, set Allow use as tooltip.
2. Page size, Type, Tooltip.
3. Put `Average` of danceability and energy, plus `Track Count`, on the page. Canvas settings can stay narrow.
4. On the Overview band chart, Format, General, Tooltips, set the type to Report page and pick Tooltip.

Drillthrough:

1. On the track table page (Countries, or a new page named Tracks), drag `dim_artist[country]` onto Drillthrough in the visual well. Keep all filters on.
2. On the country bar, right-click a country, Drillthrough, Tracks. The table should show only that country. Add a back button. Action, type Back.

Sync slicers:

1. Copy the cohort slicer onto every page except where a page filter already locks the cohort.
2. View, Sync slicers. Sync the snapshot slicer and the cohort slicer across Overview, Half-time, and Eligible. Do not sync the cohort slicer onto the Countries page if that page is locked to one cohort. A synced slicer shares its selection. That is the point of the feature, and it is also how you break a page by accident. The Countries page should stay on the Spotify tracks dataset unless you filter `chart_market` instead of artist country.

### Usability, accessibility, and the rest of the visual skills

- Alt text on the band chart and both scatters. State the comparison and the filter, for example "Column chart of the share of the top 100 tracks in each raw tempo band, African cohort in pink and hip-hop in cyan."
- Tab order follows the page title, then the slicer, then the cards, then the charts. Selection pane order is the tab order.
- Data labels are on, so the chart is not carried by color alone.
- Conditional formatting: on the track table, font color or data bars on `tempo_raw`. On the raw gap card, a rule is optional. Negative means the African median is lower. Do not color that red as if it were a failure.
- Sort the band charts by `sort_order`, not by the measure. A chart sorted by share hides the tempo scale.
- Mobile layout: View, Mobile layout. Stack the title, the slicer, Track Count, Median Tempo Raw, and the band chart. Desktop and phone do not have to show every card.
- Export: File, Options, Report settings. For a report you might publish, summarized data is the conservative export setting. The underlying rows are already public in this repo, so either setting is honest. Know where the switch is.
- Interactions: Format, Edit interactions. The gap cards should not go blank when you click a band. If they do, the band filter is reaching a measure that was not supposed to ignore it. `Median Tempo Raw Gap` ignores the cohort slicer only. A band click should still change `Median Tempo Raw`. That difference is worth clicking through once.
- If your Desktop build offers a narrative visual or a suggested page, point it at the cards and compare the sentences with the README. Keep the visual only if the sentences match these figures. A fluent sentence with the wrong median is a wrong visual.

## 4. Manage and secure Power BI

Do this section when you have a license to publish. Until then, know the answers.

### Create and manage workspaces and assets

1. Publish to a workspace you can manage, not My workspace, if you want the app exercise. My workspace cannot host an app.
2. In the service, create an app from the workspace. Put the Overview page in the navigation. An audience can be the whole organization or a list of people. You do not need a second audience for this study build.
3. Pin `Median Tempo Raw` to a dashboard if you want to see where a data alert would be configured. Do not expect the alert to fire. This dataset does not refresh onto new tempos. An alert on a tile that never changes is a good way to learn that alerts watch the refreshed value.
4. Promote the semantic model if you want the endorsement practice. Promote is something you can do to your own content. Certify is a tenant permission you may not have. The exam asks for the difference.
5. Scheduled refresh: Import from a laptop path does not refresh in the service. You either put the CSVs somewhere the service can read (OneDrive or SharePoint for this small folder) or you install an on-premises data gateway on a machine that can see the folder. A gateway is the wrong extra moving part if OneDrive already reaches the files. Know which case needs the gateway: a source the service cannot see, such as a file on a private network or a database inside a firewall.
6. Distribution: the app is the distribution method for a report you want people to consume without giving them workspace membership. A link to the workspace is how you work with editors.

### Secure and govern Power BI items

Workspace roles and row-level security are different layers. A workspace Viewer can open the app. Row-level security decides which rows the model returns. One does not replace the other.

Practice role:

1. In Desktop, Modeling, Manage roles. New role, name it Africa only.
2. On `dim_cohort`, add the filter `cohort_id` = `africa_popular`. DAX for the role filter:

```dax
[cohort_id] = "africa_popular"
```

3. Modeling, View as, Africa only. Track Count on Overview should fall from 200 to 100, and the hip-hop bars should disappear.
4. Stop viewing as. Save. Publish. In the service, dataset security, assign a colleague or a test account to the role. Membership of the role is the part you cannot finish alone.
5. A second role with no filter is not required. People who should see both cohorts simply are not members of Africa only. Do not add a role whose filter is `TRUE` unless you have a reason.

Item-level access: in the workspace, a person can be a Viewer of the workspace and still be limited by the role. Build permission on the semantic model is what lets someone create a new report on top of yours. Do not give build permission to the practice role just to see if it works.

Sensitivity labels: if the tenant has them, this report is public study material. Do not mark it confidential. The tracks are from a public dataset.

This role is study practice. The CSV is on disk and the data is public. Row-level security does not make the file private.

## Alternate model exercise: one band table, inactive relationship

Skip this if the reference-table model already works. It is here because the exam also uses `USERELATIONSHIP`.

1. Delete the relationship to `dim_tempo_band_corrected` and delete that table.
2. Draw a second relationship from `dim_tempo_band[band_key]` to `fact_track[corrected_band_key]`. Desktop will mark it inactive.
3. A visual cannot use an inactive relationship by itself. A measure can:

```dax
Corrected Band Track Count =
CALCULATE (
    [Track Count],
    USERELATIONSHIP ( fact_track[corrected_band_key], dim_tempo_band[band_key] )
)
```

4. Put `band_label` on the axis and `Corrected Band Track Count` on the values. Do not also leave the reference table in the model or you will have two ways to filter the same key and no clear story.

Use one design, not both. The reference table is the one the rest of this guide assumes.

## When the model is finished

You should be able to say, without looking at the README:

- Why the Africa cohort is an artist list and not `track_genre = afrobeat`.
- Why the hip-hop numbers are a genre proxy.
- Why the raw medians do not show a meaningful gap and why the corrected medians do, and why the 160 BPM window takes that gap away.
- Why popularity is averaged.
- Why the corrected band table is a reference query.
- Why the gap measure clears the cohort slicer and does not clear `is_top100`.

Those six answers are the analysis and the exam, in one model.
