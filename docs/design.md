# User Experience

  - When ambiguous, offer options, integrating with `fzf` for each
    matching
  - Simple commands, simple scope, composable
  - Text-based
  - Microformats to capture data
  - Integration with web interface?

# Entities

## Microformats

  - *hashtag*: A `#hashtag` to reference a topic
  - *reference*: An `[internal reference]`
  - *terms*: Terms `_term_`
  - *Date*: `2021-09-09`
  - *Time*: `10:00:20`
  - *Datetime*: `2021-09-09T10:00:20`
  - *URL*: `http://github.com/sebastien/nota`
  - *Field*: `-- field=value`, used to capture/define metadata for the
    current block or document.
  - *Block*: `-- name:type field=value`, used to break down the document
    in smaller blocks.

## Blocks

## Rich Formats

Bookmarks

    ```
    http://github.com/sebastien/nota
    Main repository for Nota
    #cli #notes #tool
    2021-09-09
    ```

defined as

    URL
    DESCRIPTION
    TAG*
    DATETIME?

# Store

`~/.config/nota/$NOTEBOOK`

## Git integration

Automatic commit, push/pull by default.

# Implementation

  - *Filesystem backend*: we're working with hierarchical text
    documents, which makes using the filesystem a good option.
