Decision Tree Classifier
========================

The Decision Tree Classifier is a simple yet powerful classification algorithm that makes decisions based on asking a series of questions about the features.

Example usage:

.. code-block:: python

   from nltk.classify import DecisionTreeClassifier

   # Prepare your labeled data
   train_data = [
       ({'feature1': 'yes', 'feature2': 'no'}, 'classA'),
       ({'feature1': 'no', 'feature2': 'yes'}, 'classB'),
       # ... more training data ...
   ]

   # Create and train the classifier
   classifier = DecisionTreeClassifier(max_depth=5)
   classifier.train(train_data)

   # Classify new data
   result = classifier.classify({'feature1': 'yes', 'feature2': 'no'})
   print(result)  # Output: 'classA' or 'classB'

The DecisionTreeClassifier uses information gain to determine the best features to split on at each node of the tree.
