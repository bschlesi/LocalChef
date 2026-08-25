* update the data stuff so it will just write a file if it doesn't see a pantry.csv - probably good practice if this ever gets ported over to another device
* remove all the emojis from the ui because it makes it look much lower effort in my opinion
* if/when the recipe generation prompt gets beefed up and made more strict we should also improve the shopping list prompt as well
* see if I can get qwen3.5 to work that would be great. given current laptop specs I can't a qwen3.5 larger than 4b to run fast enough, but even that model might be better than phi4-mini. Problem I've ran in with testing though is that qwen thinks so much, meaning by the time you get to the target token range for the output there's been a combined thought+response token count of like 2k+
* Live storing of ingredients: right now I'd have to manually go in every time i use an ingredient, but if I'm primarily using the LocalChef generated recipes then I have all the stuff I just used already reported. just have a button after a response is finished that's like "I made this recipe - remove these ingredients" or something like that
* recipe history tracker: once the button is in place to see if user made recipe, we'd then have the ability to store the recipes the user liked. this data could then most relevantly be used for the shopping generation
* historic pantry: similar ideas as recipe used tracker but the more data that can be stored on what the user does locally the better likely. maybe could be used for shopping list generation, more examples for the model generation in prompts, maybe other stuff too?
* redesign the ui because it looks like the inspiration (me) took 2 minutes to make (it did)
* make the readme more for the "ive never seen anything like this" crowd, really the user-not-developer crowd

