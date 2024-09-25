### Notes on Sphinx and addons

This repository uses sphinx with some addons to build documentation and then deploy it to Github pages. The deployment only occurs when changes are made to main, and changes are published to the `gh-pages` branch which are then served via the page. 

We use the [MyST](https://myst-parser.readthedocs.io/en/latest/index.html) parser which lets us use a mixture of markdown and reStructuredText in documentation - though the latter is preferred by sphinx. 

#### Using MyST admonitions
To use [MyST admonitions](https://myst-parser.readthedocs.io/en/latest/sphinx_admonitions.html), you need to use backticks instead of triple colons, ie. 

\`\`\`{tip}\
Let's give readers a helpful hint!\
\`\`\`

becomes

```{tip}
Let's give readers a helpful hint!
```

