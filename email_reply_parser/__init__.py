"""
    email_reply_parser is a python library port of GitHub's Email Reply Parser.

    For more information, visit https://github.com/zapier/email-reply-parser
"""

import re


class EmailReplyParser(object):
    """ Represents a email message that is parsed.
    """

    @staticmethod
    def read(text):
        """ Factory method that splits email into list of fragments

            text - A string email body

            Returns an EmailMessage instance
        """
        return EmailMessage(text).read()

    @staticmethod
    def parse_reply(text):
        """ Provides the reply portion of email.

            text - A string email body

            Returns reply body message
        """
        return EmailReplyParser.read(text).reply

    @staticmethod
    def parse_chain(text):
        """ Provides the email chain portion (quoted/forwarded content).

            text - A string email body

            Returns email chain content
        """
        return EmailReplyParser.read(text).chain


class EmailMessage(object):
    """ An email message represents a parsed email body.
    """

    SIG_REGEX = re.compile(r'(--|__|-\w)|(^Sent from my (\w+\s*){1,3})')
    QUOTE_HDR_REGEX = re.compile('On.*wrote:$')
    QUOTED_REGEX = re.compile(r'(>+)')
    HEADER_REGEX = re.compile(r'^\*?(From|Sent|To|Subject):\*? .+')
    # More specific regex for From headers that contain email addresses
    FROM_EMAIL_REGEX = re.compile(r'^\*?From:\*?.*@.*')
    # More specific regex for To headers that contain email addresses
    TO_EMAIL_REGEX = re.compile(r'^\*?To:\*?.*@.*')
    # More specific regex for Sent headers that contain date/time patterns
    SENT_EMAIL_REGEX = re.compile(r'^\*?Sent:\*?.*\d{1,2}.*\d{4}.*')
    # More specific regex for Subject headers
    SUBJECT_EMAIL_REGEX = re.compile(r'^\*?Subject:\*?.*')
    # Regex for asterisk-wrapped headers (Outlook format)
    ASTERISK_HEADER_REGEX = re.compile(r'^\*?(From|Sent|To|Subject):\*?.*')
    # Regex for concatenated headers (multiple headers on one line)
    CONCATENATED_HEADERS_REGEX = re.compile(r'From:.*Sent:.*To:.*Subject:')
    _MULTI_QUOTE_HDR_REGEX = r'(?!On.*On\s.+?wrote:)(On\s(.+?)wrote:)'
    MULTI_QUOTE_HDR_REGEX = re.compile(_MULTI_QUOTE_HDR_REGEX, re.DOTALL | re.MULTILINE)
    MULTI_QUOTE_HDR_REGEX_MULTILINE = re.compile(_MULTI_QUOTE_HDR_REGEX, re.DOTALL)

    def __init__(self, text):
        self.fragments = []
        self.fragment = None
        self.text = text.replace('\r\n', '\n')
        self.found_visible = False

    def read(self):
        """ Creates new fragment for each line
            and labels as a signature, quote, or hidden.

            Returns EmailMessage instance
        """

        self.found_visible = False

        is_multi_quote_header = self.MULTI_QUOTE_HDR_REGEX_MULTILINE.search(self.text)
        if is_multi_quote_header:
            self.text = self.MULTI_QUOTE_HDR_REGEX.sub(is_multi_quote_header.groups()[0].replace('\n', ''), self.text)

        # Fix any outlook style replies, with the reply immediately above the signature boundary line
        #   See email_2_2.txt for an example
        self.text = re.sub('([^\n])(?=\n ?[_-]{7,})', '\\1\n', self.text, re.MULTILINE)

        # Fix inline headers by adding line breaks before them
        # This helps parse headers that appear without line breaks
        # Only split when we detect a complete email header sequence with email addresses
        # Look for From: with email address followed by other headers
        self.text = re.sub(r'(?<!\n)(?<!\*)(From:[^@\n]*@[^\n]*?(?:Sent:|To:|Subject:)[^\n]*?(?:Sent:|To:|Subject:))', r'\n\1', self.text)

        self.lines = self.text.split('\n')
        self.lines.reverse()

        for line in self.lines:
            self._scan_line(line)

        self._finish_fragment()

        self.fragments.reverse()

        return self

    @property
    def reply(self):
        """ Captures reply message within email
        """
        reply = []
        for f in self.fragments:
            if not (f.hidden or f.quoted):
                reply.append(f.content)
        return '\n'.join(reply)

    @property
    def chain(self):
        """ Captures email chain content (quoted/forwarded portions)
        """
        chain = []
        for f in self.fragments:
            if f.hidden or f.quoted:
                chain.append(f.content)
        return '\n'.join(chain)

    def _scan_line(self, line):
        """ Reviews each line in email message and determines fragment type

            line - a row of text from an email message
        """
        is_quote_header = self.QUOTE_HDR_REGEX.match(line) is not None
        is_quoted = self.QUOTED_REGEX.match(line) is not None
        
        # Check for asterisk-wrapped headers first (Outlook format)
        is_asterisk_header = self.ASTERISK_HEADER_REGEX.match(line) is not None and line.count('*') >= 2
        
        # Check for concatenated headers (multiple headers on one line)
        is_concatenated_headers = self.CONCATENATED_HEADERS_REGEX.search(line) is not None
        
        # Use more specific logic for regular headers to avoid matching body text
        is_from_header = line.startswith('From:') and not line.startswith('*From:') and self.FROM_EMAIL_REGEX.match(line) is not None
        is_to_header = line.startswith('To:') and not line.startswith('*To:') and self.TO_EMAIL_REGEX.match(line) is not None
        is_sent_header = line.startswith('Sent:') and not line.startswith('*Sent:') and self.SENT_EMAIL_REGEX.match(line) is not None
        is_subject_header = line.startswith('Subject:') and not line.startswith('*Subject:') and self.SUBJECT_EMAIL_REGEX.match(line) is not None
        
        is_header = is_quote_header or is_asterisk_header or is_concatenated_headers or is_from_header or is_to_header or is_sent_header or is_subject_header

        if self.fragment and len(line.strip()) == 0:
            last_line = self.fragment.lines[-1].strip()
            if self.SIG_REGEX.match(last_line):
                # Check if this looks like a real signature or content
                is_signature = False
                
                if last_line.startswith('Sent from my'):
                    is_signature = True
                elif last_line.startswith('--') and not any(c.isalpha() for c in last_line):
                    # Pure dash separators like "--------" 
                    # Only apply look-ahead for long dash lines (8+ characters) that might be content separators
                    if len(last_line) >= 8:
                        # Check if there's substantial content after this line that suggests it's a content separator
                        remaining_lines = self.text.split('\n')[self.text.count('\n', 0, self.text.find(last_line)) + 1:]
                        
                        # Look for signs this is quoted content (email headers, etc.) vs meaningful content
                        has_email_headers = any('From:' in line or 'Sent:' in line or 'Subject:' in line for line in remaining_lines[:5])
                        meaningful_content_lines = [l for l in remaining_lines if l.strip() and len(l.strip()) > 20 and not l.strip().startswith('*') and 'From:' not in l and 'Sent:' not in l]
                        
                        # Only treat as content separator if there's substantial meaningful content AND no email headers
                        if len(meaningful_content_lines) >= 3 and not has_email_headers:
                            pass  # Don't mark as signature - treat as content separator
                        else:
                            is_signature = True
                    else:
                        # Short dash patterns like "--" are always signatures
                        is_signature = True
                elif last_line.startswith('__') and not any(c.isalpha() for c in last_line):
                    # Pure underscore separators
                    is_signature = True
                elif last_line.startswith('-') and len(last_line.split()) <= 3:
                    # Single dash lines - check if it's part of a bullet list
                    # Count consecutive lines starting with single dash
                    consecutive_dash_lines = 0
                    for i in range(len(self.fragment.lines) - 1, -1, -1):
                        line_content = self.fragment.lines[i].strip()
                        if line_content.startswith('-') and not line_content.startswith('--'):
                            consecutive_dash_lines += 1
                        else:
                            break
                    
                    # If there are multiple consecutive dash lines, it's likely a bullet list (content)
                    # If it's just one line, it's likely a signature
                    if consecutive_dash_lines == 1:
                        is_signature = True
                
                if is_signature:
                    self.fragment.signature = True
                    self._finish_fragment()

        if self.fragment \
                and ((self.fragment.headers == is_header and self.fragment.quoted == is_quoted) or
                         (self.fragment.quoted and (is_quote_header or len(line.strip()) == 0))):

            self.fragment.lines.append(line)
        else:
            self._finish_fragment()
            self.fragment = Fragment(is_quoted, line, headers=is_header)

    def quote_header(self, line):
        """ Determines whether line is part of a quoted area

            line - a row of the email message

            Returns True or False
        """
        return self.QUOTE_HDR_REGEX.match(line[::-1]) is not None

    def _finish_fragment(self):
        """ Creates fragment
        """

        if self.fragment:
            self.fragment.finish()
            if self.fragment.headers:
                # Regardless of what's been seen to this point, if we encounter a headers fragment,
                # all the previous fragments should be marked hidden and found_visible set to False.
                self.found_visible = False
                for f in self.fragments:
                    f.hidden = True
            if not self.found_visible:
                if self.fragment.quoted \
                        or self.fragment.headers \
                        or self.fragment.signature \
                        or (len(self.fragment.content.strip()) == 0):

                    self.fragment.hidden = True
                else:
                    self.found_visible = True
            self.fragments.append(self.fragment)
        self.fragment = None


class Fragment(object):
    """ A Fragment is a part of
        an Email Message, labeling each part.
    """

    def __init__(self, quoted, first_line, headers=False):
        self.signature = False
        self.headers = headers
        self.hidden = False
        self.quoted = quoted
        self._content = None
        self.lines = [first_line]

    def finish(self):
        """ Creates block of content with lines
            belonging to fragment.
        """
        self.lines.reverse()
        self._content = '\n'.join(self.lines)
        self.lines = None

    @property
    def content(self):
        return self._content.strip()
