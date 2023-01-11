# -*- coding: utf-8 -*-
"""image_classification.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1_TkE7v0lrisz5i-g27pmQRI1BfQR1uTR
"""

# Import packages

import os
import datetime
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
from tensorflow import keras
from tensorflow.keras import layers,optimizers,losses,metrics,callbacks,applications
from keras import Sequential, Model
from keras.utils import image_dataset_from_directory, plot_model
from keras.applications.mobilenet_v2 import preprocess_input, MobileNetV2
from keras.layers import RandomFlip, RandomRotation, RandomZoom
from keras.layers import Input, GlobalAveragePooling2D, Dense, Dropout
from keras.callbacks import EarlyStopping, TensorBoard, ReduceLROnPlateau, ModelCheckpoint
from sklearn.metrics import classification_report

#%% 1. Data loading

# Thank you sir Warren for showing the ways on how to download the dataset :-)

# Download the dataset
!wget https://prod-dcd-datasets-cache-zipfiles.s3.eu-west-1.amazonaws.com/5y9wdsg2zt-2.zip

# Unzip and extract into a dataset file
!unzip "5y9wdsg2zt-2.zip"

!pip install unrar

!unrar x "/content/Concrete Crack Images for Classification.rar" "/content/sample_data/dataset"

DATASET_PATH = os.path.join(os.getcwd(), 'sample_data', 'dataset')
IMAGE_SIZE = (128, 128)
BATCH_SIZE = 64
SEED = 12345

# Load the dataset as a tensorflow dataset

train_ds = image_dataset_from_directory(DATASET_PATH, batch_size=BATCH_SIZE, image_size=IMAGE_SIZE, seed=SEED, validation_split=0.2, subset='training')

val_ds = image_dataset_from_directory(DATASET_PATH, batch_size=BATCH_SIZE, image_size=IMAGE_SIZE, seed=SEED, validation_split=0.2, subset='validation')

#%% 2. Data inspection

CLASS_NAME = train_ds.class_names

# Ensure that images are propely loaded

plt.figure(figsize=(10,10))
for images, labels in train_ds.take(1):
    for i in range(9):
        plt.subplot(3,3,i+1)
        plt.imshow(images[i].numpy().astype(np.uint8))
        plt.title(CLASS_NAME[labels[i]])
        plt.axis(False)
plt.show()

#%% 3. Data preparation
# Validation test split for batches dataset

batches = tf.data.experimental.cardinality(val_ds)
test_ds = val_ds.take(batches // 2)
val_ds = val_ds.skip(batches // 2)

print('Number of validation batches: %d' % tf.data.experimental.cardinality(val_ds))
print('Number of test batches: %d' % tf.data.experimental.cardinality(test_ds))

# Convert Batchdataset into PrefetchDataset

AUTOTUNE = tf.data.AUTOTUNE

train_pf = train_ds.cache().prefetch(buffer_size=AUTOTUNE)
val_pf = val_ds.cache().prefetch(buffer_size=AUTOTUNE)
test_pf = test_ds.cache().prefetch(buffer_size=AUTOTUNE)

#%% Create a small pipeline for image augmentation

data_augmentation = keras.Sequential()
data_augmentation.add(layers.RandomFlip('horizontal'))
data_augmentation.add(layers.RandomRotation(0.2))

# Apply data augmentation on one image to test it out

for images,labels in train_ds.take(1):
    first_image = images[0]
    plt.figure(figsize=(10,10))
    for i in range(9):
        plt.subplot(3,3,i+1)
        augmented_image = data_augmentation(tf.expand_dims(first_image,axis=0))
        plt.imshow(augmented_image[0]/255.0)
        plt.axis('off')

#%% 4. Model development
# Apply transfer learning
#A) Import mobilenet v3 large

preprocess_input = applications.mobilenet_v2.preprocess_input

IMG_SHAPE = IMAGE_SIZE + (3,)

base_model = applications.MobileNetV2(input_shape=IMG_SHAPE,include_top=False,weights='imagenet')

# Set trainable model to false

base_model.trainable = False
base_model.summary()
keras.utils.plot_model(base_model,show_shapes=True)

#%% 5. Define the classification layer

#Create the classifier
#Create the global average pooling layer
global_avg = layers.GlobalAveragePooling2D()

#Create an output layer
output_layer = layers.Dense(len(CLASS_NAME),activation='softmax')

# Use functional API to create the entire model pipeline

inputs = keras.Input(shape=IMG_SHAPE)

x = data_augmentation(inputs)
x = preprocess_input(x)
x = base_model(x,training=False)
x = global_avg(x)
x = layers.Dropout(0.3)(x)
outputs = output_layer(x)

model = keras.Model(inputs=inputs,outputs=outputs)
model.summary()

# Compile the model

optimizer = optimizers.Adam(learning_rate = 0.0001)
loss = losses.SparseCategoricalCrossentropy()
model.compile(optimizer=optimizer,loss=loss,metrics=['accuracy'])

# Evaluate before model training

loss0, acc0 = model.evaluate(test_ds)
print("Evaluation Before Training")
print("Loss =",loss0)
print("Accuracy =",acc0)

# Commented out IPython magic to ensure Python compatibility.
#%% 6.Tensorboard callback 
# %load_ext tensorboard

LOGS_PATH = os.path.join(os.getcwd(),'logs',datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
ts_callback = TensorBoard(log_dir=LOGS_PATH)
es_callback = EarlyStopping(monitor='val_loss',patience=5,verbose=0,restore_best_weights=True)

#%% 7. Model training
EPOCHS = 8

history = model.fit(train_pf, validation_data=val_pf, epochs=EPOCHS, callbacks=[es_callback,ts_callback])

#%% 8. Model evaluation
# Doing prediction with model

image_batch, label_batch = test_pf.as_numpy_iterator().next()
y_pred = np.argmax(model.predict(image_batch), axis=1)

# Classification report
print('Classification report:\n', classification_report(label_batch, y_pred))

# %% Model saving
# Save model
model.save(filepath=os.path.join(os.getcwd(), 'saved_model', 'model.h5'))

# Commented out IPython magic to ensure Python compatibility.
# %tensorboard --logdir logs