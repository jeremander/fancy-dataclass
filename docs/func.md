It is a common pattern to consolidate a bundle of function parameters into a dataclass.

For example, let's say we've written an algorithm to train a [neural network](https://en.wikipedia.org/wiki/Neural_network_(machine_learning)). You might start out writing it like this:

```python
def train_neural_network(
    input_data: list,
    num_layers: int = 3,
    neurons_per_layer: int = 128,
    num_iterations: int = 1000,
    learning_rate: float = 0.1,
    verbose: bool = False
) -> object:
    """Train a neural network from data."""
    ...
```

However, the large number of parameters can start to become unwieldy. You can use a dataclass to refactor:

```python
from dataclasses import dataclass


@dataclass
class TrainNeuralNetwork:
    """Class for training a neural network."""
    num_layers: int = 3
    neurons_per_layer: int = 128
    num_iterations: int = 1000
    learning_rate: float = 0.1
    verbose: bool = False

    def train(self, input_data: list) -> object:
        """Train the neural network from data."""
        ...
```

Now the parameters have become dataclass fields, which you can customize when constructing `TrainNeuralNetwork`, e.g.

```python
trainer = TrainNeuralNetwork(num_layers=5, verbose=True)
model = trainer.train(input_data)
```

You are also at liberty to define other methods on the class. For example, you could use [`__post_init__`](https://docs.python.org/3/library/dataclasses.html#dataclasses.__post_init__) to validate the parameters, and you could add a method `init_neural_network` to initialize the neural net structure and weights prior to training.

## Partial Function as Dataclass

While the approach above is recommended in complex situations, `fancy_dataclass` offers an alternative feature that can convert the `train_neural_network` function into the `TrainNeuralNetwork` dataclass automatically:

```python
from fancy_dataclass import func_dataclass


# def train_neural_network(...)

# wrap the function into a dataclass
TrainNeuralNetwork = func_dataclass(train_neural_network, method_name='train')

trainer = TrainNeuralNetwork(num_layers=5, verbose=True)
model = trainer.train(input_data)
```

`func_dataclass` takes a regular function as input and converts it into a new dataclass type with a single method named `method_name` (in this case, `train`). The dataclass's fields will be the function's keyword arguments, and the inputs to the method will be the positional arguments. In other words, it turns the function into a _partial function_ whose keyword parameters are supplied at initialization time, and whose core logic is only invoked when the method is called.

If you omit `method_name`, it will default to `__call__`, which lets you call the object directly as a function. So instead of `trainer.train(input_data)` you would just write `trainer(input_data)`.

Another advantage to this approach is that you can supply one or more base classes to `func_dataclass` to provide extra functionality; in particular you can use various `fancy_dataclass` mixins such as [`JSONDataclass`](json.md):

```python
from fancy_dataclass import JSONDataclass, func_dataclass


# def train_neural_network(...)

# wrap the function into a JSON-serializable dataclass
TrainNeuralNetwork = func_dataclass(train_neural_network, bases=JSONDataclass)

trainer = TrainNeuralNetwork(num_layers=5, verbose=True)

# the function becomes the __call__ method by default, so just call the object
model = trainer(input_data)

# serialize the training parameters
print(trainer.to_json_string(indent=2))
```

Output:

```json
{
  "num_layers": 5,
  "verbose": true
}
```

This makes it easy to define a single class that can both run your function logic and serialize its own parameters.

<style>
.md-sidebar--secondary {
    display: none !important;
}

.md-main__inner .md-content {
    max-width: 45rem;
}
</style>
