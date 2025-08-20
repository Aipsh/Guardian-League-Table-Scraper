Hi! 

I made this in Pycharm. To use, just download GUG Scraper.py and paste it into whatever you use and hit run.

This is a very poorly written script but it's pretty much the first thing I made
using bits and pieces I found elsewhere. I hope it's useful to someone and could hopefully be used as the basis for the other league tables (except of course the daily mail because nobody wants to read that)
Please forgive my use of emojis I just think it's funny.
if they're causing issues, just search for these and delete them:

👍🙂‍↔️🛜💾🫸

Don't worry - it won't save any of that stuff in the CSVs. This is safe for work (if they even allow you to run scripts at work)

Right now what it will do when run is: 
1) ask you for a place to create two folders
2) ask you for the URL of the entire league table you want to scrape
3) ask you for the university name you're interested in.
    for example if you only want oxford subjects, type oxford and hit enter.  It will only save the subject files where oxford appears in the ranking.  But beware, you'll need to type exactly how it appears in the league table. Oxford will also not include oxford brookes for example. If you want everything, either type all or just hit enter.
4) Next it will ask you for another year, where you will again be asked for the university

Currently it only does two years, but you can just do it again for all the years :)
The folders will be saved as C:/Yourstuff/gug_2020.at 2025-Aug-20_12.00

It takes the gug_xxxx from the first year as it appears in the guardian url.
I've tested it with all the league table years and it works for all of them.
---------------------------------------
Very brief explanation of how it works:

Essentially it uses requests and beautifulsoup to take the overview.json from the main table page
(e.g. https://interactive.guim.co.uk/atoms/labs/2021/08/university-guide/v/1655133428819/assets/data/overview.json)
You can find it by going to the url:
https://www.theguardian.com/education/ng-interactive/2024/sep/07/the-guardian-university-guide-2025-the-rankings 
Pressing F12, going to the network tab and refreshing the page. You should see overview.json pop up.

Luckily, if you copy that link and paste it into the search bar you will see at the bottom of the JSON mess a list of guardian subject codes and their names. Handy!

We can use those to append to the original json overview link (and removing overview.json first) -
so
https://interactive.guim.co.uk/atoms/labs/2021/08/university-guide/v/1655133428819/assets/data/overview.json

becomes

https://interactive.guim.co.uk/atoms/labs/2021/08/university-guide/v/1655133428819/assets/data/S250.json

and now we have the subject table too! Before I even realised this I was trying all sorts of nonsense using webdriver to literally select
the subject list and try to scrape the json by checking if _anything at all changed on the page._ 
It was very stupid and frustrating, and I didn't think to keep the network tab open while I picked different options on the subject list. Whoops!

It will also save a list of subjects for the year and a list of subjects your university of choice appeared in and didn't appear in.
Hope this helps! I'm not experienced so if anyone could make this ruthlessly more efficient I'd appreciate it. Especially so if you use it to make other league table scrapers.

All the best,
Aipsh
