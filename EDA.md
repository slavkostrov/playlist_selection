# Exploratory data analysis

Audio embeddings are not ready yet, so EDA was done only for meta information.

## Data description

Meta information consists of 3 main parts:

**General track info**

Basic audio track features, such as:

- Track name
- Artist name
- Album name
- Release date
- Genre
- Duration

**Spotify audio description**

Additional information about track, which describes its audio parameters:

- Popularity
- Danceability
- Loudness
- Speechiness
- Acousticness
- Tempo
- Instrumentalness
- Valence

**Audio analysis features**

Number and mean duration for audio track parts:

- Bars
- Beats
- Tatums
- Sections
- Segments

## Data validation

To validate how good tracks meta and mp3 are matching, we compared tracks duration from this 2 sources.

![image](https://github.com/slavkostrov/playlist_selection/assets/56652212/b1c9a5ab-f899-4229-9b90-3ebcebd8f67f)

As a result we can see that main part of tracks has pretty much the same duration in meta and mp3.

## Features distributions

Tracks were collected by random sampling in such a way to get uniform distribution by genre.

**Genre distribution**

In fact, genre distribution is really close to uniform.

![image](https://github.com/slavkostrov/playlist_selection/assets/56652212/d5b955fa-0ada-4ec8-b383-903034821486)

**Release year**

For release year data has notable bias towards 2000s tracks. But in general number of tracks for each era is adequate.

![image](https://github.com/slavkostrov/playlist_selection/assets/56652212/6fd9f073-c3fe-4edb-a3c6-fc19847e623f)

**Duration in seconds**

Duration has close to normal distribution with long tail towards right border.

![image](https://github.com/slavkostrov/playlist_selection/assets/56652212/dd7ebc46-1e36-4b11-b7f4-8487a7467dcf)


## Features representativeness

To estimate how good collected features are we did several visualizations.

**t-SNE**

From t-SNE visualization we can see that with collected features we can separate some genres clouds, which is pretty
good considering we are watching on only 2 components.

![image](https://github.com/slavkostrov/playlist_selection/assets/56652212/5b45b2e3-4674-4cc1-a67c-da5cda50bcd5)


**Audio features vs genres**

As we can see the picture below seems pretty logical: certain genres has more pronounced audio features than others.

![image](https://github.com/slavkostrov/playlist_selection/assets/56652212/a987fbe5-70b6-4f50-9267-a9070b22e5e9)
