from typing import Protocol

from typeguard import typechecked


# An example of extension/inheritance/sub-/super/(whatever) classes in Python.
class Shape(Protocol):
    def area(self) -> float: ...


class Circle:
    def __init__(self, radius: float):
        self.radius = radius

    def area(self) -> float:
        return 3.14 * self.radius**2


class Rectangle:
    def __init__(self, height: float, width: float):
        self.height = height
        self.width = width

    def area(self) -> float:
        return self.height * self.width


@typechecked
def calculate_area(shape: Shape) -> float:
    return shape.area()


circle = Circle(5)
rectangle = Rectangle(2, 6)

# print(calculate_area(circle))  # No error, structural typing matches.
# print(calculate_area(rectangle))  # No error, structural typing matches.
