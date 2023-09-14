import re

def remove_html(text):
  if text is not None:
    re.sub('<[^<]+?>', '', text)
  return text