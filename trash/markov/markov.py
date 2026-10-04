import markovify

# Get raw text as string.
with open('standardoil.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# Build the model.
text_model = markovify.Text(text, state_size=3)

# Print five randomly-generated sentences
for i in range(5):
    print(text_model.make_sentence())
    print("")

# Print three randomly-generated sentences of no more than 280 characters
for i in range(3):
    print(text_model.make_short_sentence(280))
    print("")