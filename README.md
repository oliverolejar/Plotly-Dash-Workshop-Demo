# Plotly-Dash-Workshop-Demo

A small workshop demo for people who are hesitant to code but still want to work with data.

- `notebooks/01_plotly_intro.ipynb` shows how an interactive chart gets *built*, step by step, in Python with Plotly Express.
- `app/app.py` hands that same Gapminder chart to someone who never touches the code: pick continents from a dropdown, drag the year slider, sort or filter the table - the chart and table update live, no code involved.

## Running it

```bash
pixi install

# the notebook
pixi run jupyter lab

# the interactive app
pixi run app
```

The app starts at http://127.0.0.1:8050.
