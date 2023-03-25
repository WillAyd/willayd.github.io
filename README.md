Steps for publishing are modified from https://docs.getpelican.com/en/latest/tips.html#user-pages

```sh
pelican content -o output -s publishconf.py
ghp-import output -b gh-pages
git push -f git@github.com:willayd/willayd.github.io.git gh-pages:gh-pages
```
