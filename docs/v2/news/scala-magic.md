## JupyterLab Integration supports a simple Scala integration

The `%%scala` magic will send Scala code to the same Spark Context

Note:

- This is a experimental feature
- Every JupyterLab Integration notebook starts 2 executions contexts (one for python, one for Scala)
- No Spark progressbar
- No Scala autocompletion

![scala-magic](scala-magic.gif)