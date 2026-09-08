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
 * question asked — see `BlockTextArea.handlePaste`. Only tabs and real
 * `<table>` markup say "there is data here"; a screenshot has neither, and
 * neither does an image copied off a web page.
 */
export function carriesTable(clipboard: DataTransfer | null): boolean {
  if (clipboard === null) {
    return false;
  }
  if (/<table[\s>]/i.test(clipboard.getData("text/html"))) {
    return true;
  }
  const text = clipboard.getData("text/plain");
  return text.includes("\t") && text.trim().includes("\n");
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
