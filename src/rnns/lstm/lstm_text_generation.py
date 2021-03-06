"""
Use LSTM to generate new text from Nietzsche's writings.

At least 20 epochs are required before the generated text sounds coherent.
It is recommended to run this script on GPU, due to computational costs.
If you try this script on new data, make sure your corpus
has at least ~100k characters. ~1M is better.
"""

from __future__ import print_function
from keras.models import Sequential
from keras.layers import Dense, Activation
from keras.layers import LSTM
from keras.optimizers import RMSprop
import numpy as np
import random
import sys
import os
import h5py


os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # suppress TF installation warning
# available corpuses: nietzsche / zarathustra / zarathustra_ger
corpus = 'zarathustra_ger'

# load corpus
path = os.path.join('data', 'lstm_text_generation', corpus + '.txt')
text = open(path).read().lower()
print('corpus length:', len(text))

# assign integer value to each character
chars = sorted(list(set(text)))
print('total chars:', len(chars))
char_indices = dict((c, i) for i, c in enumerate(chars))
indices_char = dict((i, c) for i, c in enumerate(chars))

# cut the text in semi-redundant character sequences
maxlen = 40
step = 3
sentences = []
next_chars = []
for i in range(0, len(text) - maxlen, step):
    sentences.append(text[i: i + maxlen])  # i = 1
    next_chars.append(text[i + maxlen])
print('nb sequences:', len(sentences))

print('Vectorization...')
X = np.zeros((len(sentences), maxlen, len(chars)), dtype=np.bool)
y = np.zeros((len(sentences), len(chars)), dtype=np.bool)
for i, sentence in enumerate(sentences):
    for t, char in enumerate(sentence):
        X[i, t, char_indices[char]] = 1
    y[i, char_indices[next_chars[i]]] = 1


# build the model: a single LSTM
print('Build model...')
model = Sequential()
model.add(LSTM(128, input_shape=(maxlen, len(chars))))
model.add(Dense(len(chars)))
model.add(Activation('softmax'))
model.compile(loss='categorical_crossentropy', optimizer=RMSprop(lr=0.01))


def sample(preds, temperature=1.0):
    """Sample an index from a probability array (the net's prediction)."""
    preds = np.asarray(preds).astype('float64')
    preds = np.log(preds) / temperature
    exp_preds = np.exp(preds)
    preds = exp_preds / np.sum(exp_preds)
    probas = np.random.multinomial(1, preds, 1)
    return np.argmax(probas)


def generate_text(model):
    """Generate text from LSTM model."""
    start_index = random.randint(0, len(text) - maxlen - 1)

    for diversity in [0.2, 0.5, 1.0, 1.2]:
        print()
        print('\n----- diversity:', diversity)

        generated = ''
        sentence = text[start_index: start_index + maxlen]
        generated += sentence
        print('----- Generating with seed: "' + sentence + '"')
        sys.stdout.write(generated)

        for i in range(400):
            x = np.zeros((1, maxlen, len(chars)))
            for t, char in enumerate(sentence):
                x[0, t, char_indices[char]] = 1.

            preds = model.predict(x, verbose=0)[0]
            next_index = sample(preds, diversity)
            next_char = indices_char[next_index]

            generated += next_char
            sentence = sentence[1:] + next_char

            sys.stdout.write(next_char)
            sys.stdout.flush()


# selecting iterations to generate text for
# get_text = [1, 5, 10, 15, 20]
get_text = [40, 80, 120, 160]

# train the model, output generated text after each iteration
for i in range(1, 161):
    print()
    print('-' * 50)
    print('Iteration', i)
    # load saved weights or train
    model_path = os.path.join('models',
                              'lstm_text_generation',
                              'lstm_' + corpus + '_' + str(i) + '.hdf5')
    if os.path.isfile(model_path):
        print("Loading model weights from file:" + model_path)
        model.load_weights(model_path)
    else:
        print("No weights saved at location " + model_path + ". Computing...")
        model.fit(X, y,  # X.shape
                  batch_size=128,
                  epochs=1)
        # save weights
        model.save_weights(model_path)

    # generate text from model (if in get_text list)
    if i in get_text:
        generate_text(model)
