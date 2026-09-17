# Plotly-Dash-Workshop-Demo

A Plotly/Dash demo built for the MIND Symposium at Robarts Research Institute. It shows
how an abstracted, no-code frontend can let someone manipulate and visualize data - the
same pattern that could sit in front of the Khan Lab's SPIMquant tool output. This repo
teaches that pattern with a small generic dataset (Gapminder) so it's easy to follow
without needing real lab data.

- `archived/01_plotly_intro.ipynb` shows how an interactive chart gets *built*, step by step, in Python with Plotly Express.
- `demo/generic_app.py` hands that same Gapminder chart to someone who never touches the code: pick continents from a dropdown, drag the year slider, sort or filter the table - the chart and table update live, no code involved.

## Running it

```bash
pixi install

# the notebook
pixi run notebook

# the interactive generic app
pixi run generic_app
```

The app starts at http://127.0.0.1:8050.
