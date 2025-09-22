import os
import sys
import unittest
import re

import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from email_reply_parser import EmailReplyParser


class EmailMessageTest(unittest.TestCase):
    def test_simple_body(self):
        message = self.get_email('email_1_1')

        self.assertEqual(3, len(message.fragments))
        self.assertEqual(
            [False, True, True],
            [f.signature for f in message.fragments]
        )
        self.assertEqual(
            [False, True, True],
            [f.hidden for f in message.fragments]
        )
        self.assertTrue("folks" in message.fragments[0].content)
        self.assertTrue("-Abhishek Kona" in message.fragments[1].content)
        self.assertTrue(message.fragments[1].hidden or message.fragments[1].quoted)
        self.assertTrue("riak-users" in message.fragments[2].content)

    def test_reads_bottom_message(self):
        message = self.get_email('email_1_2')

        self.assertEqual(6, len(message.fragments))
        self.assertEqual(
            [False, True, False, True, False, False],
            [f.quoted for f in message.fragments]
        )

        self.assertEqual(
            [False, False, False, False, False, True],
            [f.signature for f in message.fragments]
        )

        self.assertEqual(
            [False, False, False, True, True, True],
            [f.hidden for f in message.fragments]
        )

        self.assertTrue("Hi," in message.fragments[0].content)
        self.assertTrue("On" in message.fragments[1].content)
        self.assertTrue(">" in message.fragments[3].content)
        self.assertTrue("riak-users" in message.fragments[5].content)

    def test_reads_inline_replies(self):
        message = self.get_email('email_1_8')
        self.assertEqual(7, len(message.fragments))

        self.assertEqual(
            [True, False, True, False, True, False, False],
            [f.quoted for f in message.fragments]
        )

        self.assertEqual(
            [False, False, False, False, False, False, True],
            [f.signature for f in message.fragments]
        )

        self.assertEqual(
            [False, False, False, False, True, True, True],
            [f.hidden for f in message.fragments]
        )

    def test_reads_top_post(self):
        message = self.get_email('email_1_3')

        self.assertEqual(5, len(message.fragments))

    def test_multiline_reply_headers(self):
        message = self.get_email('email_1_6')
        self.assertTrue('I get' in message.fragments[0].content)
        self.assertTrue('On' in message.fragments[1].content)

    def test_captures_date_string(self):
        message = self.get_email('email_1_4')

        self.assertTrue('Awesome' in message.fragments[0].content)
        self.assertTrue('On' in message.fragments[1].content)
        self.assertTrue('Loader' in message.fragments[1].content)

    def test_complex_body_with_one_fragment(self):
        message = self.get_email('email_1_5')

        self.assertEqual(1, len(message.fragments))

    def test_newline_before_bullet_points(self):
        """Test that parser correctly handles newlines before bullet points in reply content."""
        # Read the raw email content
        with open('test/emails/dashes.txt') as f:
            email_content = f.read()
        
        # The parsed reply should include the bullet points and the final line
        parsed_reply = EmailReplyParser.parse_reply(email_content)
        
        # Expected exact content
        expected_reply = """Hi Ellie,
Oh - sorry, looks like the formatting of my below email was a bit off. Sharing the details
again for the event if you can make it:

-Upskilling and reskilling our workforce
-Something else
-Another thing

You'll also hear from zyz"""
        
        self.assertEqual(expected_reply, parsed_reply)

    def test_verify_reads_signature_correct(self):
        message = self.get_email('correct_sig')
        self.assertEqual(2, len(message.fragments))

        self.assertEqual(
            [False, False],
            [f.quoted for f in message.fragments]
        )

        self.assertEqual(
            [False, True],
            [f.signature for f in message.fragments]
        )

        self.assertEqual(
            [False, True],
            [f.hidden for f in message.fragments]
        )

        self.assertTrue('--' in message.fragments[1].content)

    def test_deals_with_windows_line_endings(self):
        msg = self.get_email('email_1_7')

        self.assertTrue(':+1:' in msg.fragments[0].content)
        self.assertTrue('On' in msg.fragments[1].content)
        self.assertTrue('Steps 0-2' in msg.fragments[1].content)

    def test_reply_is_parsed(self):
        message = self.get_email('email_1_2')
        self.assertTrue("You can list the keys for the bucket" in message.reply)

    def test_reply_from_gmail(self):
        with open('test/emails/email_gmail.txt') as f:
            self.assertEqual('This is a test for inbox replying to a github message.',
                             EmailReplyParser.parse_reply(f.read()))

    def test_parse_out_just_top_for_outlook_reply(self):
        with open('test/emails/email_2_1.txt') as f:
            self.assertEqual("Outlook with a reply", EmailReplyParser.parse_reply(f.read()))

    def test_parse_out_just_top_for_outlook_with_reply_directly_above_line(self):
        with open('test/emails/email_2_2.txt') as f:
            self.assertEqual("Outlook with a reply directly above line", EmailReplyParser.parse_reply(f.read()))

    def test_parse_out_just_top_for_outlook_with_unusual_headers_format(self):
        with open('test/emails/email_2_3.txt') as f:
            self.assertEqual(
                "Outlook with a reply above headers using unusual format",
                EmailReplyParser.parse_reply(f.read()))

    def test_sent_from_iphone(self):
        with open('test/emails/email_iPhone.txt') as email:
            self.assertTrue("Sent from my iPhone" not in EmailReplyParser.parse_reply(email.read()))

    def test_email_one_is_not_on(self):
        with open('test/emails/email_one_is_not_on.txt') as email:
            self.assertTrue(
                "On Oct 1, 2012, at 11:55 PM, Dave Tapley wrote:" not in EmailReplyParser.parse_reply(email.read()))

    def test_partial_quote_header(self):
        message = self.get_email('email_partial_quote_header')
        self.assertTrue("On your remote host you can run:" in message.reply)
        self.assertTrue("telnet 127.0.0.1 52698" in message.reply)
        self.assertTrue("This should connect to TextMate" in message.reply)

    def test_email_headers_no_delimiter(self):
        message = self.get_email('email_headers_no_delimiter')
        self.assertEqual(message.reply.strip(), 'And another reply!')

    def test_multiple_on(self):
        message = self.get_email("greedy_on")
        self.assertTrue(re.match('^On your remote host', message.fragments[0].content))
        self.assertTrue(re.match('^On 9 Jan 2014', message.fragments[1].content))

        self.assertEqual(
            [False, True, False],
            [fragment.quoted for fragment in message.fragments]
        )

        self.assertEqual(
            [False, False, False],
            [fragment.signature for fragment in message.fragments]
        )

        self.assertEqual(
            [False, True, True],
            [fragment.hidden for fragment in message.fragments]
        )

    def test_pathological_emails(self):
        t0 = time.time()
        message = self.get_email("pathological")
        self.assertTrue(time.time() - t0 < 1, "Took too long")

    def test_doesnt_remove_signature_delimiter_in_mid_line(self):
        message = self.get_email('email_sig_delimiter_in_middle_of_line')
        self.assertEqual(1, len(message.fragments))

    def test_inline_email_body_format(self):
        """Test parsing of email with inline headers in email_body.txt"""
        message = self.get_email('email_body')
        
        # Test that the latest reply is extracted correctly
        reply = EmailReplyParser.parse_reply(message.text)
        self.assertEqual("New email body", reply)
        
    def test_email_with_from_in_body(self):
        """Test parsing of email that contains 'From:' text in the body"""
        message = self.get_email('email_with_from_in_body')
        
        # Test that the latest reply is extracted correctly
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """Here is my reply to your message.

From: the beginning, I thought this was a good idea. I sent you an email yesterday about this topic. To summarize what we discussed, I think we should proceed."""
        self.assertEqual(expected_reply, reply)

    def test_email_with_sent_in_body(self):
        """Test parsing of email that contains 'Sent:' text in the body"""
        message = self.get_email('email_with_sent_in_body')
        
        # Test that the latest reply is extracted correctly
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """Here is my reply to your message.

I sent you an email yesterday about this topic. To summarize what we discussed, I think we should proceed."""
        self.assertEqual(expected_reply, reply)

    def test_email_with_to_in_body(self):
        """Test parsing of email that contains 'To:' text in the body"""
        message = self.get_email('email_with_to_in_body')
        
        # Test that the latest reply is extracted correctly
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """Here is my reply to your message.

To summarize what we discussed, I think we should proceed. To be clear, I want to make sure we're on the same page."""
        self.assertEqual(expected_reply, reply)

    def test_email_with_subject_in_body(self):
        """Test parsing of email that contains 'Subject:' text in the body"""
        message = self.get_email('email_with_subject_in_body')
        
        # Test that the latest reply is extracted correctly
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """Here is my reply to your message.

Subject to change, I think we should proceed. The subject matter is quite important."""
        self.assertEqual(expected_reply, reply)

    def test_email_case_insensitive_headers(self):
        """Test parsing of email with lowercase header words in body text"""
        message = self.get_email('email_case_insensitive_headers')
        
        # Test that the latest reply is extracted correctly
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """Here is my reply to your message.

from: the beginning, I thought this was a good idea. I sent you an email yesterday about this topic. To summarize what we discussed, I think we should proceed."""
        self.assertEqual(expected_reply, reply)

    def test_email_all_lowercase_headers(self):
        """Test parsing of email with all lowercase header words in body text"""
        message = self.get_email('email_all_lowercase_headers')
        
        # Test that the latest reply is extracted correctly
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """Here is my reply to your message.

from: the beginning, I thought this was a good idea.
sent: you an email yesterday about this topic.
to: summarize what we discussed, I think we should proceed.
subject: to change, I think we should proceed."""
        self.assertEqual(expected_reply, reply)

    def test_email_whole_is_first(self):
        """Test parsing of email where the whole content is considered the first email"""
        message = self.get_email('email_whole_is_first')
        
        # Test that the latest reply is extracted correctly
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """New email body
From: Jonathan
To: Jeremy
Hey wassup?"""
        self.assertEqual(expected_reply, reply)

    def test_email_body_unusual(self):
        """Test parsing of email with unusual body format where the whole content is considered the first email"""
        message = self.get_email('email_body_unusual')
        
        # Test that the latest reply is extracted correctly
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """New body

From: Someone
To: Another person

More stuff here"""
        self.assertEqual(expected_reply, reply)

    def test_parse_chain_empty_for_simple_email(self):
        """Test that parse_chain returns empty string for emails with no quoted content"""
        message = self.get_email('email_1_5')
        
        # Test that parse_chain returns empty string for simple email
        chain = EmailReplyParser.parse_chain(message.text)
        self.assertEqual("", chain)

    def test_parse_chain_with_quoted_content(self):
        """Test that parse_chain returns quoted content for emails with chain"""
        message = self.get_email('email_1_2')
        
        # Test that parse_chain returns the quoted content
        chain = EmailReplyParser.parse_chain(message.text)
        self.assertNotEqual("", chain)
        self.assertTrue("On" in chain)  # Should contain quote header
        self.assertTrue(">" in chain)   # Should contain quoted content

    def test_parse_chain_for_email_with_from_in_body(self):
        """Test that parse_chain returns the chain content for email_with_from_in_body"""
        message = self.get_email('email_with_from_in_body')
        chain = EmailReplyParser.parse_chain(message.text)
        self.assertNotEqual("", chain)
        self.assertTrue("From: sender@example.com" in chain)
        self.assertTrue("Sent: Monday, January 1, 2024 1:00 PM" in chain)
        self.assertTrue("To: recipient@example.com" in chain)
        self.assertTrue("Subject: Previous message" in chain)
        self.assertTrue("This is the previous email content." in chain)

    def test_parse_chain_for_email_with_sent_in_body(self):
        """Test that parse_chain returns the chain content for email_with_sent_in_body"""
        message = self.get_email('email_with_sent_in_body')
        chain = EmailReplyParser.parse_chain(message.text)
        self.assertNotEqual("", chain)
        self.assertTrue("From: sender@example.com" in chain)
        self.assertTrue("Sent: Monday, January 1, 2024 1:00 PM" in chain)
        self.assertTrue("To: recipient@example.com" in chain)
        self.assertTrue("Subject: Previous message" in chain)
        self.assertTrue("This is the previous email content." in chain)

    def test_parse_chain_for_email_with_to_in_body(self):
        """Test that parse_chain returns the chain content for email_with_to_in_body"""
        message = self.get_email('email_with_to_in_body')
        chain = EmailReplyParser.parse_chain(message.text)
        self.assertNotEqual("", chain)
        self.assertTrue("From: sender@example.com" in chain)
        self.assertTrue("Sent: Monday, January 1, 2024 1:00 PM" in chain)
        self.assertTrue("To: recipient@example.com" in chain)
        self.assertTrue("Subject: Previous message" in chain)
        self.assertTrue("This is the previous email content." in chain)

    def test_parse_chain_for_email_with_subject_in_body(self):
        """Test that parse_chain returns the chain content for email_with_subject_in_body"""
        message = self.get_email('email_with_subject_in_body')
        chain = EmailReplyParser.parse_chain(message.text)
        self.assertNotEqual("", chain)
        self.assertTrue("From: sender@example.com" in chain)
        self.assertTrue("Sent: Monday, January 1, 2024 1:00 PM" in chain)
        self.assertTrue("To: recipient@example.com" in chain)
        self.assertTrue("Subject: Previous message" in chain)
        self.assertTrue("This is the previous email content." in chain)


    def test_parse_reply_and_chain_for_email_1_1(self):
        """Test that parse_reply and parse_chain work correctly for email_1_1"""
        message = self.get_email('email_1_1')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """Hi folks

What is the best way to clear a Riak bucket of all key, values after 
running a test?
I am currently using the Java HTTP API."""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain
        chain = EmailReplyParser.parse_chain(message.text)
        expected_chain = """-Abhishek Kona
_______________________________________________
riak-users mailing list
riak-users@lists.basho.com
http://lists.basho.com/mailman/listinfo/riak-users_lists.basho.com"""
        self.assertEqual(expected_chain, chain)

    def test_parse_reply_and_chain_for_email_1_2(self):
        """Test that parse_reply and parse_chain work correctly for email_1_2"""
        message = self.get_email('email_1_2')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        # Just check that the reply contains the expected content
        self.assertTrue("Hi," in reply)
        self.assertTrue("You can list the keys for the bucket" in reply)
        self.assertTrue("String bucket = \"my_bucket\"" in reply)
        self.assertTrue("you’ll need to delete them all individually" in reply)
        
        # Test parse_chain
        chain = EmailReplyParser.parse_chain(message.text)
        expected_chain = """On Tue, 2011-03-01 at 18:02 +0530, Abhishek Kona wrote:
> Hi folks
> 
> What is the best way to clear a Riak bucket of all key, values after 
> running a test?
> I am currently using the Java HTTP API.
> 
> -Abhishek Kona
> 
> 
> _______________________________________________
> riak-users mailing list
> riak-users@lists.basho.com
> http://lists.basho.com/mailman/listinfo/riak-users_lists.basho.com

_______________________________________________
riak-users mailing list
riak-users@lists.basho.com
http://lists.basho.com/mailman/listinfo/riak-users_lists.basho.com"""
        self.assertEqual(expected_chain, chain)

    def test_parse_reply_and_chain_for_email_1_3(self):
        """Test that parse_reply and parse_chain work correctly for email_1_3"""
        message = self.get_email('email_1_3')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """Oh thanks.

Having the function would be great."""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain
        chain = EmailReplyParser.parse_chain(message.text)
        expected_chain = """-Abhishek Kona
On 01/03/11 7:07 PM, Russell Brown wrote:
> Hi,
> On Tue, 2011-03-01 at 18:02 +0530, Abhishek Kona wrote:
>> Hi folks
>>
>> What is the best way to clear a Riak bucket of all key, values after
>> running a test?
>> I am currently using the Java HTTP API.
> You can list the keys for the bucket and call delete for each. Or if you
> put the keys (and kept track of them in your test) you can delete them
> one at a time (without incurring the cost of calling list first.)
>
> Something like:
>
>          String bucket = "my_bucket";
>          BucketResponse bucketResponse = riakClient.listBucket(bucket);
>          RiakBucketInfo bucketInfo = bucketResponse.getBucketInfo();
>
>          for(String key : bucketInfo.getKeys()) {
>              riakClient.delete(bucket, key);
>          }
>
>
> would do it.
>
> See also
>
> http://wiki.basho.com/REST-API.html#Bucket-operations
>
> which says
>
> "At the moment there is no straightforward way to delete an entire
> Bucket. There is, however, an open ticket for the feature. To delete all
> the keys in a bucket, you’ll need to delete them all individually."
>
>> -Abhishek Kona
>>
>>
>> _______________________________________________
>> riak-users mailing list
>> riak-users@lists.basho.com
>> http://lists.basho.com/mailman/listinfo/riak-users_lists.basho.com
>

_______________________________________________
riak-users mailing list
riak-users@lists.basho.com
http://lists.basho.com/mailman/listinfo/riak-users_lists.basho.com"""
        self.assertEqual(expected_chain, chain)

    def test_parse_reply_and_chain_for_email_1_4(self):
        """Test that parse_reply and parse_chain work correctly for email_1_4"""
        message = self.get_email('email_1_4')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """Awesome! I haven't had another problem with it."""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain
        chain = EmailReplyParser.parse_chain(message.text)
        expected_chain = """On Aug 22, 2011, at 7:37 PM, defunkt<reply@reply.github.com> wrote:




> Loader seems to be working well.
"""
        self.assertEqual(expected_chain, chain)

    def test_parse_reply_and_chain_for_email_1_5(self):
        """Test that parse_reply and parse_chain work correctly for email_1_5"""
        message = self.get_email('email_1_5')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """One: Here's what I've got.

- This would be the first bullet point that wraps to the second line
to the next
- This is the second bullet point and it doesn't wrap
- This is the third bullet point and I'm having trouble coming up with enough
to say
- This is the fourth bullet point

Two:
- Here is another bullet point
- And another one

This is a paragraph that talks about a bunch of stuff. It goes on and on
for a while."""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain - should be empty string since there's no quoted content
        chain = EmailReplyParser.parse_chain(message.text)
        self.assertEqual("", chain)

    def test_parse_reply_and_chain_for_email_1_7(self):
        """Test that parse_reply and parse_chain work correctly for email_1_7"""
        message = self.get_email('email_1_7')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """:+1:"""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain
        chain = EmailReplyParser.parse_chain(message.text)
        expected_chain = """On Tue, Sep 25, 2012 at 8:59 AM, Chris Wanstrath<notifications@github.com>wrote:

> Steps 0-2 are in prod. Gonna let them sit for a bit then start cleaning up
> the old code with 3 & 4.
>
> 
> Reply to this email directly or view it on GitHub.
>
>
"""
        self.assertEqual(expected_chain, chain)

    def test_parse_reply_and_chain_for_email_1_8(self):
        """Test that parse_reply and parse_chain work correctly for email_1_8"""
        message = self.get_email('email_1_8')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """I will reply under this one
and under this."""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain
        chain = EmailReplyParser.parse_chain(message.text)
        expected_chain = """On Tue, Apr 29, 2014 at 4:22 PM, Example Dev <sugar@example.com>wrote:

> okay.  Well, here's some stuff I can write.
>
> And if I write a 2 second line you and maybe reply under this?
>
> Or if you didn't really feel like it, you could reply under this line.Or
> if you didn't really feel like it, you could reply under this line. Or if
> you didn't really feel like it, you could reply under this line. Or if you
> didn't really feel like it, you could reply under this line.
>
>
> okay?
>
>
> -- Tim
>
> On Tue, April 29, 2014 at 4:21 PM, Tim Haines <tmhaines@example.com> wrote:
> > hi there
> >
> > After you reply to this I'm going to send you some inline responses.
> >
> > --
> > Hey there, this is my signature
>
>
>

--
Hey there, this is my signature"""
        self.assertEqual(expected_chain, chain)

    def test_parse_reply_and_chain_for_email_2_1(self):
        """Test that parse_reply and parse_chain work correctly for email_2_1"""
        message = self.get_email('email_2_1')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """Outlook with a reply"""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain
        chain = EmailReplyParser.parse_chain(message.text)
        expected_chain = """------------------------------
*From:* Google Apps Sync Team [mailto:mail-noreply@google.com]
*Sent:* Thursday, February 09, 2012 1:36 PM
*To:* jow@xxxx.com
*Subject:* Google Apps Sync was updated!
Dear Google Apps Sync user,

Google Apps Sync for Microsoft Outlook® was recently updated. Your computer
now has the latest version (version 2.5). This release includes bug fixes
to improve product reliability. For more information about these and other
changes, please see the help article here:

http://www.google.com/support/a/bin/answer.py?answer=153463

Sincerely,

The Google Apps Sync Team."""
        self.assertEqual(expected_chain, chain)

    def test_parse_reply_and_chain_for_email_2_2(self):
        """Test that parse_reply and parse_chain work correctly for email_2_2"""
        message = self.get_email('email_2_2')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """Outlook with a reply directly above line"""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain
        chain = EmailReplyParser.parse_chain(message.text)
        expected_chain = """________________________________________
From: CRM Comments [crm-comment@example.com]
Sent: Friday, 23 March 2012 5:08 p.m.
To: John S. Greene
Subject: [contact:106] John Greene
A new comment has been added to the Contact named 'John Greene':

I am replying to a comment."""
        self.assertEqual(expected_chain, chain)

    def test_parse_reply_and_chain_for_email_2_3(self):
        """Test that parse_reply and parse_chain work correctly for email_2_3"""
        message = self.get_email('email_2_3')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """Outlook with a reply above headers using unusual format"""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain
        chain = EmailReplyParser.parse_chain(message.text)
        expected_chain = """*From:* Kim via Site [mailto:noreply@site.com]
*Sent:* Monday, January 15, 2018 2:15 AM
*To:* user@xxxxx.com
*Subject:* You have a new message!
Respond to Kim by replying directly to this email

New message from Kim on Site:

    Ei tale aliquam eum, at vel tale sensibus, an sit vero magna. Vis no veri
    clita, movet detraxit inciderint te est. Mel nusquam perfecto repudiandae
    ei. Error paulo pri ea. At partem offendit appetere sea, no vis audiam
    latine appellantur.

    Sea id aperiam accusam, vel dico omnesque qualisque cu. Cu nec alii euismod
    eloquentiam. Ea nisl utinam vis. Est impetus intellegam dissentiet et. Nec
    ea rationibus percipitur, eam fugit impetus ad, ad possit semper recusabo
    quo."""
        self.assertEqual(expected_chain, chain)

    def test_parse_reply_and_chain_for_email_all_lowercase_headers(self):
        """Test that parse_reply and parse_chain work correctly for email_all_lowercase_headers"""
        message = self.get_email('email_all_lowercase_headers')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """Here is my reply to your message.

from: the beginning, I thought this was a good idea.
sent: you an email yesterday about this topic.
to: summarize what we discussed, I think we should proceed.
subject: to change, I think we should proceed."""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain
        chain = EmailReplyParser.parse_chain(message.text)
        expected_chain = """From: sender@example.com
Sent: Monday, January 1, 2024 1:00 PM
To: recipient@example.com
Subject: Previous message
This is the previous email content."""
        self.assertEqual(expected_chain, chain)

    def test_parse_reply_and_chain_for_email_BlackBerry(self):
        """Test that parse_reply and parse_chain work correctly for email_BlackBerry"""
        message = self.get_email('email_BlackBerry')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """Here is another email"""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain
        chain = EmailReplyParser.parse_chain(message.text)
        expected_chain = """Sent from my BlackBerry"""
        self.assertEqual(expected_chain, chain)

    def test_parse_reply_and_chain_for_email_body_unusual(self):
        """Test that parse_reply and parse_chain work correctly for email_body_unusual"""
        message = self.get_email('email_body_unusual')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """New body

From: Someone
To: Another person

More stuff here"""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain - should be empty string since there's no quoted content
        chain = EmailReplyParser.parse_chain(message.text)
        self.assertEqual("", chain)

    def test_parse_reply_and_chain_for_email_body(self):
        """Test that parse_reply and parse_chain work correctly for email_body"""
        message = self.get_email('email_body')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """New email body"""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain
        chain = EmailReplyParser.parse_chain(message.text)
        expected_chain = """From: Diego Siciliani <DiegoS@sqxt.onmicrosoft.com>Sent: Saturday, August 16, 2025 9:19 PMTo: Diego Siciliani <DiegoS@sqxt.onmicrosoft.com>Subject: Fw: Excitement \xa0
From: Diego Siciliani <DiegoS@sqxt.onmicrosoft.com>Sent: Saturday, August 16, 2025 9:18 PMTo: Diego Siciliani <DiegoS@sqxt.onmicrosoft.com>Subject: Re: Excitement \xa0This is a second reply.This time a bit more complex and fun 🤩\xa0Above me is a sample image.Some cheeky html:<!DOCTYPE html><html><body><h1>My First Heading</h1><p>My first paragraph.</p></body></html>Did it work?
From: Diego Siciliani <DiegoS@sqxt.onmicrosoft.com>Sent: Saturday, August 16, 2025 9:07 PMTo: Diego Siciliani <DiegoS@sqxt.onmicrosoft.com>Subject: Re: Excitement \xa0This is the first reply
From: Diego Siciliani <DiegoS@sqxt.onmicrosoft.com>Sent: Wednesday, June 18, 2025 3:21 PMTo: Diego Siciliani <DiegoS@sqxt.onmicrosoft.com>Subject: Excitement \xa0Another exciting message"""
        self.assertEqual(expected_chain, chain)

    def test_parse_reply_and_chain_for_email_bullets(self):
        """Test that parse_reply and parse_chain work correctly for email_bullets"""
        message = self.get_email('email_bullets')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """test 2 this should list second

and have spaces

and retain this formatting


   - how about bullets
   - and another"""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain
        chain = EmailReplyParser.parse_chain(message.text)
        expected_chain = """On Fri, Feb 24, 2012 at 10:19 AM, <examples@email.goalengine.com> wrote:

> Give us an example of how you applied what they learned to achieve
> something in your organization

-- 

*Joe Smith | Director, Product Management*"""
        self.assertEqual(expected_chain, chain)

    def test_parse_reply_and_chain_for_email_case_insensitive_headers(self):
        """Test that parse_reply and parse_chain work correctly for email_case_insensitive_headers"""
        message = self.get_email('email_case_insensitive_headers')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """Here is my reply to your message.

from: the beginning, I thought this was a good idea. I sent you an email yesterday about this topic. To summarize what we discussed, I think we should proceed."""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain
        chain = EmailReplyParser.parse_chain(message.text)
        expected_chain = """From: sender@example.com
Sent: Monday, January 1, 2024 1:00 PM
To: recipient@example.com
Subject: Previous message
This is the previous email content."""
        self.assertEqual(expected_chain, chain)

    def test_parse_reply_and_chain_for_email_gmail(self):
        """Test that parse_reply and parse_chain work correctly for email_gmail"""
        message = self.get_email('email_gmail')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """This is a test for inbox replying to a github message."""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain
        chain = EmailReplyParser.parse_chain(message.text)
        expected_chain = """On Wed, May 18, 2016 at 11:10 PM Steven Scott <notifications@github.com>wrote:
That way people can tell how outdated their version is, mostly because I'm
personally too lazy to increment a version number all the time 👍

—
You are receiving this because you are subscribed to this thread.
Reply to this email directly or view it on GitHub"""
        self.assertEqual(expected_chain, chain)

    def test_parse_reply_and_chain_for_email_headers_no_delimiter(self):
        """Test that parse_reply and parse_chain work correctly for email_headers_no_delimiter"""
        message = self.get_email('email_headers_no_delimiter')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """And another reply!"""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain
        chain = EmailReplyParser.parse_chain(message.text)
        expected_chain = """From: Dan Watson [mailto:user@host.com]
Sent: Monday, November 26, 2012 10:48 AM
To: Watson, Dan
Subject: Re: New Issue
A reply
--
Sent from my iPhone
On Nov 26, 2012, at 10:27 AM, "Watson, Dan" <user@host2.com> wrote:
This is a message.
With a second line."""
        self.assertEqual(expected_chain, chain)

    def test_parse_reply_and_chain_for_email_iPhone(self):
        """Test that parse_reply and parse_chain work correctly for email_iPhone"""
        message = self.get_email('email_iPhone')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """Here is another email"""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain
        chain = EmailReplyParser.parse_chain(message.text)
        expected_chain = """Sent from my iPhone"""
        self.assertEqual(expected_chain, chain)

    def test_parse_reply_and_chain_for_email_multi_word_sent_from_my_mobile_device(self):
        """Test that parse_reply and parse_chain work correctly for email_multi_word_sent_from_my_mobile_device"""
        message = self.get_email('email_multi_word_sent_from_my_mobile_device')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """Here is another email"""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain
        chain = EmailReplyParser.parse_chain(message.text)
        expected_chain = """Sent from my Verizon Wireless BlackBerry"""
        self.assertEqual(expected_chain, chain)

    def test_parse_reply_and_chain_for_email_one_is_not_on(self):
        """Test that parse_reply and parse_chain work correctly for email_one_is_not_on"""
        message = self.get_email('email_one_is_not_on')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """Thank, this is really helpful.

One outstanding question I had:

Locally (on development), when I run..."""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain
        chain = EmailReplyParser.parse_chain(message.text)
        self.assertTrue("On Oct 1, 2012, at 11:55 PM, Dave Tapley wrote:" in chain)
        self.assertTrue("The good news is that I've found a much better query for lastLocation." in chain)

    def test_parse_reply_and_chain_for_email_partial_quote_header(self):
        """Test that parse_reply and parse_chain work correctly for email_partial_quote_header"""
        message = self.get_email('email_partial_quote_header')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """On your remote host you can run:

     telnet 127.0.0.1 52698

This should connect to TextMate (on your Mac, via the tunnel). If that 
fails, the tunnel is not working."""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain
        chain = EmailReplyParser.parse_chain(message.text)
        expected_chain = """On 9 Jan 2014, at 2:47, George Plymale wrote:

> I am having an odd issue wherein suddenly port forwarding stopped 
> working in a particular scenario for me.  By default I have ssh set to 
> use the following config (my ~/.ssh/config file):
> […]
"""
        self.assertEqual(expected_chain, chain)

    def test_parse_reply_and_chain_for_email_sent_from_my_not_signature(self):
        """Test that parse_reply and parse_chain work correctly for email_sent_from_my_not_signature"""
        message = self.get_email('email_sent_from_my_not_signature')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """Here is another email"""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain
        chain = EmailReplyParser.parse_chain(message.text)
        expected_chain = """Sent from my desk, is much easier then my mobile phone."""
        self.assertEqual(expected_chain, chain)

    def test_parse_reply_and_chain_for_email_sig_delimiter_in_middle_of_line(self):
        """Test that parse_reply and parse_chain work correctly for email_sig_delimiter_in_middle_of_line"""
        message = self.get_email('email_sig_delimiter_in_middle_of_line')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """Hi there!

Stuff happened.

And here is a fix -- this is not a signature.

kthxbai"""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain - should be empty string since there's no quoted content
        chain = EmailReplyParser.parse_chain(message.text)
        self.assertEqual("", chain)

    def test_parse_reply_and_chain_for_email_whole_is_first(self):
        """Test that parse_reply and parse_chain work correctly for email_whole_is_first"""
        message = self.get_email('email_whole_is_first')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """New email body
From: Jonathan
To: Jeremy
Hey wassup?"""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain - should be empty string since there's no quoted content
        chain = EmailReplyParser.parse_chain(message.text)
        self.assertEqual("", chain)

    def test_parse_reply_and_chain_for_correct_sig(self):
        """Test that parse_reply and parse_chain work correctly for correct_sig"""
        message = self.get_email('correct_sig')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """this is an email with a correct -- signature."""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain
        chain = EmailReplyParser.parse_chain(message.text)
        expected_chain = """-- 
rick"""
        self.assertEqual(expected_chain, chain)

    def test_parse_reply_and_chain_for_greedy_on(self):
        """Test that parse_reply and parse_chain work correctly for greedy_on"""
        message = self.get_email('greedy_on')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """On your remote host you can run:

     telnet 127.0.0.1 52698

This should connect to TextMate (on your Mac, via the tunnel). If that
fails, the tunnel is not working."""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain
        chain = EmailReplyParser.parse_chain(message.text)
        expected_chain = """On 9 Jan 2014, at 2:47, George Plymale wrote:

> I am having an odd issue wherein suddenly port forwarding stopped
> working in a particular scenario for me.  By default I have ssh set to
> use the following config (my ~/.ssh/config file):
> […]
> ---
> Reply to this email directly or view it on GitHub:
> https://github.com/textmate/rmate/issues/29
"""
        self.assertEqual(expected_chain, chain)

    def test_parse_reply_and_chain_for_pathological(self):
        """Test that parse_reply and parse_chain work correctly for pathological"""
        message = self.get_email('pathological')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """I think you're onto something. I will try to fix the problem as soon as I
get back to a computer."""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain - use substring checks for this complex case
        chain = EmailReplyParser.parse_chain(message.text)
        self.assertTrue("On Dec 8, 2013 2:10 PM, \"John Sullivan\" <notifications@github.com> wrote:" in chain)
        self.assertTrue("I think your code is shortening the reference sequence" in chain)
        self.assertTrue("Influenza A virus" in chain)
        self.assertTrue("organism.sequence:" in chain)
        self.assertTrue("reference_alignment:" in chain)
        self.assertTrue("query: AGCGAAAGCAGGTCAAATATATTCAATATGGAGAGAATAAAAGAATTAAG" in chain)
        self.assertTrue("query_alignment: GCGAAAGCAGGTCAAATATATTCAATATGGAGAGAATAAAAGAATTAAG" in chain)

    def test_parse_reply_and_chain_for_email_1_6(self):
        """Test that parse_reply and parse_chain work correctly for email_1_6"""
        message = self.get_email('email_1_6')
        
        # Test parse_reply
        reply = EmailReplyParser.parse_reply(message.text)
        expected_reply = """I get proper rendering as well.

Sent from a magnificent torch of pixels"""
        self.assertEqual(expected_reply, reply)
        
        # Test parse_chain
        chain = EmailReplyParser.parse_chain(message.text)
        expected_chain = """On Dec 16, 2011, at 12:47 PM, Corey Donohoe<reply@reply.github.com>wrote:

> Was this caching related or fixed already?  I get proper rendering here.
>
> ![](https://img.skitch.com/20111216-m9munqjsy112yqap5cjee5wr6c.jpg)
>
> ---
> Reply to this email directly or view it on GitHub:
> https://github.com/github/github/issues/2278#issuecomment-3182418
"""
        self.assertEqual(expected_chain, chain)

    def get_email(self, name):
        """ Return EmailMessage instance
        """
        with open('test/emails/%s.txt' % name) as f:
            text = f.read()
        return EmailReplyParser.read(text)


if __name__ == '__main__':
    unittest.main()
