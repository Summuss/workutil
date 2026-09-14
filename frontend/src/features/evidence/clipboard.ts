/**
 * Could this paste be a query result?
 *
 * A necessary condition and nothing more. Whether a paste really is a table —
 * quoted cells, cells holding a tab or a newline, rows that turn out not to
 * line up — is settled on the server, because that is the whole reason the
 * parsing is there (design.md §6 F5) and it is not a judgement worth making
 * twice.
 *
 * It does two jobs, and the second is why it has to stay this narrow. The
 * first: it saves the round trip on every ordinary paste, and with it the
 * surprise of a sentence turning into a block the moment it is pasted —
 * without a tab or a `<table>` there is nothing a table could be cut out of,
 * so the paste stays a paste and lands in the box.
 *
 * The second: it is what a paste carrying *both* a picture and a table is
 * decided by. Excel puts a PNG of the copied cells on the clipboard beside the
 * TSV and the markup, so "is there an image flavour" cannot be the first
 * question asked — see `BlockTextArea.handlePaste`. Only tabs and real table
 * markup say "there is data here"; a screenshot has neither, and neither does
 * an image copied off a web page.
 *
 * Both halves are looser than they look like they should be, for the same
 * reason: what the clipboard actually carries is narrower than the markup a
 * table is written in.
 *
 * - `<tr>` and `<td>` count, not just `<table>`. On Windows the HTML flavour
 *   is CF_HTML, which marks a fragment inside a larger document, and Chrome
 *   hands over that fragment alone. Excel's marker sits *after* the `<table>`
 *   tag and a partial selection of a web page table starts inside one too, so
 *   what arrives is bare rows. Neither tag turns up outside a table, so this
 *   stays as narrow a question as it was.
 * - One line counts, as long as it ends in a newline. A grid hands over whole
 *   lines, terminator included, so a single record copied out of one is
 *   `a\tb\tc\n`. Trimming that away first is what used to make a one-row
 *   result set the one thing this could not see. Text pulled out of the middle
 *   of a line has no newline at all and still stays a paste.
 */
/**
 * Does this text carry the coarse markings of a table?
 *
 * Both tabs and newlines must be present: a tab alone without newlines is a
 * fragment selected out of the middle of an indented log line, and newlines
 * alone without tabs are regular paragraphs.
 */
export function hasTableMarkings(text: string): boolean {
  return text.includes("\t") && text.includes("\n");
}

export function carriesTable(clipboard: DataTransfer | null): boolean {
  if (clipboard === null) {
    return false;
  }
  if (/<(?:table|tr|td|th)[\s>]/i.test(clipboard.getData("text/html"))) {
    return true;
  }
  const text = clipboard.getData("text/plain");
  return hasTableMarkings(text);
}

/** The two flavours a pasted table can arrive in, as the server takes them. */
export interface PastedText {
  text: string;
  html: string | null;
}

export function pastedText(clipboard: DataTransfer): PastedText {
  return {
    text: clipboard.getData("text/plain"),
    html: clipboard.getData("text/html") || null,
  };
}
