LocalChef
Idea for an app that's an SLM-based cooking assistant/cooking tracking software

- The whole thing is local on a localhost website via the python \-m http: server command  
- Core tenets: pantry tracker & recipe maker; add-on tenets if possible: customization & shopping; probably impossible tenet: adapting to preference suggestions  
- Pantry feature  
  - Essentially there’d be a CSV file that updates every time I get more ingredients or run out of things  
  - Updating is done via a CSV file \- ideally looks in a specific local directory for csv, reads it if there, returns error if no csv there  
  - This information is passed into the LLM in the recipe section (prompt injection or otherwise)  
  - Stretch goal: have the app prompt the user when it thinks you’ve run out of something (for example, in the ‘pantry’ I add 16 oz pasta, then I cook a recipe using that box of pasta; at the end of the recipe there will be a prompt/button to delete that pasta)  
- Recipes & cooking feature  
  - Simplified recipe prompter \- takes information from the pantry to tailor recipes to you  
  - Example: user types in “chicken fajitas, program will call SLM to build a chicken fajitas recipe with only the things in the user’s pantry  
  - Stretch goal: log-on suggested recipes, like a button to click that generates a recipe of the SLM’s choosing (eg it sees you have everything to make fajitas so it gives you that)  
- Customization feature  
  - Area where user puts in specific prompt injections (‘always report the estimated macros with each recipe’, ‘include how to divide it up for meal-prepping’, ‘my oven isn’t working, only give me stovetop recipes’)  
- Shopping list feature  
  - An ‘I’m going shopping’ button to click that will use an SLM call to generate a base list for the user based on what’s in your pantry  
  - Example: you have everything you need to make fajitas besides onion, so add onion to your list  
  - Stretch goal: all old pantry items (things already consumed) and referenced when building list (user has bought and used a box of pasta 5 times; they’ll probably want it again)

Tech stack

- GitHub repository to store code  
- Downloaded Phi5-mini via Ollama to run SLM features  
- Code written primarily in python