# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

- What is your model name?  
VibeMaxer

---

## 2. Intended Use  

- What kind of recommendations does it generate?  
It recommends songs from a small class dataset based on a user's taste profile.  

- What assumptions does it make about the user?  
It assumes the user's profile is accurate and complete.  

- Is this for real users or classroom exploration?  
This is for classroom exploration, not production use.  

---

## 3. How the Model Works  

- What features of each song are used?  
The model uses genre, mood, energy, tempo, valence, danceability, acousticness, popularity, release decade, instrumentalness, liveness, speechiness, and detailed mood tags.  

- What user preferences are considered?  
It uses favorite genre, favorite mood, target energy, tempo preference, valence, danceability, acoustic preference, popularity target, era target, and preferred tags.  

- How does the model turn those into a score?  
It compares each song to the user profile and adds weighted points for each matching feature. Songs with higher scores rank higher.  

- What changes did you make from the starter logic?  
I added extra song attributes, multiple ranking modes, and an artist diversity penalty to reduce repeated artists.  

---

## 4. Data  

- How many songs are in the catalog?  
The dataset has 30 songs.  

- What genres or moods are represented?  
It includes genres like pop, rock, rap, lofi, jazz, and ambient. Moods include happy, chill, intense, calm, and others.  

- Did you add or remove data?  
I did not add or remove songs. I added new attributes for each song.  

- Are there parts of musical taste missing in the dataset?  
Yes. The dataset is small, so many genres and listener styles are still underrepresented.  

---

## 5. Strengths  

- Which user types get reasonable results?  
It works best for users with clear and mainstream preferences.  

- What patterns does the scoring capture correctly?  
It captures genre and mood alignment well, along with energy and tempo fit.  

- Which recommendations matched your intuition?  
For alex_pop_happy, top songs like Sunrise City and Levitating matched my expectations.  

---

## 6. Limitations and Bias 

- What features does the model not consider?  
It does not use full listening history, lyrics meaning, social influence, or context like activity and location.  

- Which genres or moods are underrepresented?  
Niche genres and less common moods have fewer songs in this small dataset.  

- Where does the system overfit to one preference?  
It can overfit to strong genre and mood matches, which can create filter bubbles.  

- How might the scoring unintentionally favor some users?  
Users with popular genres get more variety. Niche users get less variety. The artist penalty helps, but it does not fully remove this imbalance.  

---

## 7. Evaluation  

- Which user profiles did you test?  
I tested alex_pop_happy, maya_lofi_chill, and ryan_rap_intense.  

- What did you look for in the recommendations?  
I looked for genre and mood fit, numeric feature alignment, and clear reason text that matches the score logic.  

- What surprised you?  
The system narrowed quickly for niche profiles, even with many total songs in the catalog.  

- What simple tests or comparisons did you run?  
I compared outputs across profiles, tested ranking modes, and checked results before and after adding the artist diversity penalty.  

---

## 8. Future Work  

- Tune the artist penalty per profile instead of using one fixed value.  
- Lower strict genre matching so related genres can appear.  
- Add features like release year, lyrics tone, and skip behavior.  
- Support mixed tastes, like users who want both chill and upbeat songs.  
- Show short explanations in plain language for each recommendation.  

---

## 9. Personal Reflection  

- What I learned about recommender systems:  
I learned that simple scoring can work, but weights matter a lot.  

- Something unexpected I discovered:  
I was surprised by how fast the model got stuck in one genre.  

- How this changed how I think about music recommendation apps:  
This project made me notice how real apps balance accuracy and variety.  
Now I think recommendation quality should include fairness and discovery, not just match score.  
