## List notes

Listing all the notes

    » nota ls
    
    [1] tools/git: Git cheatsheet …
    [2] tools/pulumi: Pulumi Provisionning …

Listing the contents of one note

    » nota ls 1
    
    [1.1] #  Git Cheatsheet
    [1.2] ## Deleting branches
    [1.3] …

Listing the all notes with a tag

    » nota ls #python
    
    [3] tools/mypy: MyPy Cheatsheet
    [8] lang/python: Python NOtes

Listing the all notes that define a term

    » nota ls _CORS_
    
    [ 4] tools/nginx: 3 references
    [10] protocol/http: 2 references

## Searching for something

    nota search git close branch

## Create a new entry

    nota create tools/pulumi
