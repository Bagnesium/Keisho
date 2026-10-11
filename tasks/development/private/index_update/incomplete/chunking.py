def chunks(text, size=2):
    words=text.split()
    return [' '.join(words[index:index+size]) for index in range(0,len(words),size)]
