# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: exp.proto
# Protobuf Python Version: 5.29.0
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    5,
    29,
    0,
    '',
    'exp.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\texp.proto\x12\tmessaging\"?\n\x14\x43reateAccountRequest\x12\x10\n\x08username\x18\x01 \x01(\t\x12\x15\n\rpassword_hash\x18\x02 \x01(\x0c\".\n\x15\x43reateAccountResponse\x12\x15\n\rsession_token\x18\x01 \x01(\x0c\"7\n\x0cLoginRequest\x12\x10\n\x08username\x18\x01 \x01(\t\x12\x15\n\rpassword_hash\x18\x02 \x01(\x0c\"_\n\rLoginResponse\x12!\n\x06status\x18\x01 \x01(\x0e\x32\x11.messaging.Status\x12\x15\n\rsession_token\x18\x02 \x01(\x0c\x12\x14\n\x0cunread_count\x18\x03 \x01(\r\"O\n\x13ListAccountsRequest\x12\x0f\n\x07user_id\x18\x01 \x01(\r\x12\x15\n\rsession_token\x18\x02 \x01(\x0c\x12\x10\n\x08wildcard\x18\x03 \x01(\t\"@\n\x14ListAccountsResponse\x12\x15\n\raccount_count\x18\x01 \x01(\r\x12\x11\n\tusernames\x18\x02 \x03(\t\"[\n\x1a\x44isplayConversationRequest\x12\x0f\n\x07user_id\x18\x01 \x01(\r\x12\x15\n\rsession_token\x18\x02 \x01(\x0c\x12\x15\n\rconversant_id\x18\x03 \x01(\r\"O\n\x13\x43onversationMessage\x12\x12\n\nmessage_id\x18\x01 \x01(\r\x12\x13\n\x0bsender_flag\x18\x02 \x01(\x08\x12\x0f\n\x07\x63ontent\x18\x03 \x01(\t\"f\n\x1b\x44isplayConversationResponse\x12\x15\n\rmessage_count\x18\x01 \x01(\r\x12\x30\n\x08messages\x18\x02 \x03(\x0b\x32\x1e.messaging.ConversationMessage\"w\n\x12SendMessageRequest\x12\x16\n\x0esender_user_id\x18\x01 \x01(\r\x12\x15\n\rsession_token\x18\x02 \x01(\x0c\x12\x19\n\x11recipient_user_id\x18\x03 \x01(\r\x12\x17\n\x0fmessage_content\x18\x04 \x01(\t\"\x15\n\x13SendMessageResponse\"]\n\x13ReadMessagesRequest\x12\x0f\n\x07user_id\x18\x01 \x01(\r\x12\x15\n\rsession_token\x18\x02 \x01(\x0c\x12\x1e\n\x16number_of_messages_req\x18\x03 \x01(\r\"\x16\n\x14ReadMessagesResponse\"S\n\x14\x44\x65leteMessageRequest\x12\x0f\n\x07user_id\x18\x01 \x01(\r\x12\x13\n\x0bmessage_uid\x18\x02 \x01(\r\x12\x15\n\rsession_token\x18\x03 \x01(\x0c\"\x17\n\x15\x44\x65leteMessageResponse\">\n\x14\x44\x65leteAccountRequest\x12\x0f\n\x07user_id\x18\x01 \x01(\r\x12\x15\n\rsession_token\x18\x02 \x01(\x0c\"\x17\n\x15\x44\x65leteAccountResponse\"B\n\x18GetUnreadMessagesRequest\x12\x0f\n\x07user_id\x18\x01 \x01(\r\x12\x15\n\rsession_token\x18\x02 \x01(\x0c\"P\n\x11UnreadMessageInfo\x12\x13\n\x0bmessage_uid\x18\x01 \x01(\r\x12\x11\n\tsender_id\x18\x02 \x01(\r\x12\x13\n\x0breceiver_id\x18\x03 \x01(\r\"Z\n\x19GetUnreadMessagesResponse\x12\r\n\x05\x63ount\x18\x01 \x01(\r\x12.\n\x08messages\x18\x02 \x03(\x0b\x32\x1c.messaging.UnreadMessageInfo\"[\n\x1cGetMessageInformationRequest\x12\x0f\n\x07user_id\x18\x01 \x01(\r\x12\x15\n\rsession_token\x18\x02 \x01(\x0c\x12\x13\n\x0bmessage_uid\x18\x03 \x01(\r\"v\n\x1dGetMessageInformationResponse\x12\x11\n\tread_flag\x18\x01 \x01(\x08\x12\x11\n\tsender_id\x18\x02 \x01(\r\x12\x16\n\x0e\x63ontent_length\x18\x03 \x01(\r\x12\x17\n\x0fmessage_content\x18\x04 \x01(\t\")\n\x16GetUsernameByIDRequest\x12\x0f\n\x07user_id\x18\x01 \x01(\r\"+\n\x17GetUsernameByIDResponse\x12\x10\n\x08username\x18\x01 \x01(\t\"W\n\x18MarkMessageAsReadRequest\x12\x0f\n\x07user_id\x18\x01 \x01(\r\x12\x15\n\rsession_token\x18\x02 \x01(\x0c\x12\x13\n\x0bmessage_uid\x18\x03 \x01(\r\"\x1b\n\x19MarkMessageAsReadResponse\",\n\x18GetUserByUsernameRequest\x12\x10\n\x08username\x18\x01 \x01(\t\"T\n\x19GetUserByUsernameResponse\x12&\n\x06status\x18\x01 \x01(\x0e\x32\x16.messaging.FoundStatus\x12\x0f\n\x07user_id\x18\x02 \x01(\r\"g\n\x12RequestVoteRequest\x12\x0c\n\x04term\x18\x01 \x01(\x04\x12\x14\n\x0c\x63\x61ndidate_id\x18\x02 \x01(\t\x12\x16\n\x0elast_log_index\x18\x03 \x01(\x03\x12\x15\n\rlast_log_term\x18\x04 \x01(\x04\"9\n\x13RequestVoteResponse\x12\x0c\n\x04term\x18\x01 \x01(\x04\x12\x14\n\x0cvote_granted\x18\x02 \x01(\x08\")\n\x08LogEntry\x12\x0c\n\x04term\x18\x01 \x01(\x04\x12\x0f\n\x07\x63ommand\x18\x02 \x01(\t\"\xa3\x01\n\x14\x41ppendEntriesRequest\x12\x0c\n\x04term\x18\x01 \x01(\x04\x12\x11\n\tleader_id\x18\x02 \x01(\t\x12\x16\n\x0eprev_log_index\x18\x03 \x01(\x03\x12\x15\n\rprev_log_term\x18\x04 \x01(\x04\x12$\n\x07\x65ntries\x18\x05 \x03(\x0b\x32\x13.messaging.LogEntry\x12\x15\n\rleader_commit\x18\x06 \x01(\x03\"6\n\x15\x41ppendEntriesResponse\x12\x0c\n\x04term\x18\x01 \x01(\x04\x12\x0f\n\x07success\x18\x02 \x01(\x08\"\x13\n\x11LeaderPingRequest\"\x14\n\x12LeaderPingResponse*0\n\x06Status\x12\x12\n\x0eSTATUS_SUCCESS\x10\x00\x12\x12\n\x0eSTATUS_FAILURE\x10\x01*\'\n\x0b\x46oundStatus\x12\t\n\x05\x46OUND\x10\x00\x12\r\n\tNOT_FOUND\x10\x01\x32\xd1\t\n\x10MessagingService\x12R\n\rCreateAccount\x12\x1f.messaging.CreateAccountRequest\x1a .messaging.CreateAccountResponse\x12:\n\x05Login\x12\x17.messaging.LoginRequest\x1a\x18.messaging.LoginResponse\x12O\n\x0cListAccounts\x12\x1e.messaging.ListAccountsRequest\x1a\x1f.messaging.ListAccountsResponse\x12\x64\n\x13\x44isplayConversation\x12%.messaging.DisplayConversationRequest\x1a&.messaging.DisplayConversationResponse\x12L\n\x0bSendMessage\x12\x1d.messaging.SendMessageRequest\x1a\x1e.messaging.SendMessageResponse\x12O\n\x0cReadMessages\x12\x1e.messaging.ReadMessagesRequest\x1a\x1f.messaging.ReadMessagesResponse\x12R\n\rDeleteMessage\x12\x1f.messaging.DeleteMessageRequest\x1a .messaging.DeleteMessageResponse\x12R\n\rDeleteAccount\x12\x1f.messaging.DeleteAccountRequest\x1a .messaging.DeleteAccountResponse\x12^\n\x11GetUnreadMessages\x12#.messaging.GetUnreadMessagesRequest\x1a$.messaging.GetUnreadMessagesResponse\x12j\n\x15GetMessageInformation\x12\'.messaging.GetMessageInformationRequest\x1a(.messaging.GetMessageInformationResponse\x12X\n\x0fGetUsernameByID\x12!.messaging.GetUsernameByIDRequest\x1a\".messaging.GetUsernameByIDResponse\x12^\n\x11MarkMessageAsRead\x12#.messaging.MarkMessageAsReadRequest\x1a$.messaging.MarkMessageAsReadResponse\x12^\n\x11GetUserByUsername\x12#.messaging.GetUserByUsernameRequest\x1a$.messaging.GetUserByUsernameResponse\x12I\n\nLeaderPing\x12\x1c.messaging.LeaderPingRequest\x1a\x1d.messaging.LeaderPingResponse2\xaf\x01\n\x0bRaftService\x12L\n\x0bRequestVote\x12\x1d.messaging.RequestVoteRequest\x1a\x1e.messaging.RequestVoteResponse\x12R\n\rAppendEntries\x12\x1f.messaging.AppendEntriesRequest\x1a .messaging.AppendEntriesResponseb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'exp_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_STATUS']._serialized_start=2443
  _globals['_STATUS']._serialized_end=2491
  _globals['_FOUNDSTATUS']._serialized_start=2493
  _globals['_FOUNDSTATUS']._serialized_end=2532
  _globals['_CREATEACCOUNTREQUEST']._serialized_start=24
  _globals['_CREATEACCOUNTREQUEST']._serialized_end=87
  _globals['_CREATEACCOUNTRESPONSE']._serialized_start=89
  _globals['_CREATEACCOUNTRESPONSE']._serialized_end=135
  _globals['_LOGINREQUEST']._serialized_start=137
  _globals['_LOGINREQUEST']._serialized_end=192
  _globals['_LOGINRESPONSE']._serialized_start=194
  _globals['_LOGINRESPONSE']._serialized_end=289
  _globals['_LISTACCOUNTSREQUEST']._serialized_start=291
  _globals['_LISTACCOUNTSREQUEST']._serialized_end=370
  _globals['_LISTACCOUNTSRESPONSE']._serialized_start=372
  _globals['_LISTACCOUNTSRESPONSE']._serialized_end=436
  _globals['_DISPLAYCONVERSATIONREQUEST']._serialized_start=438
  _globals['_DISPLAYCONVERSATIONREQUEST']._serialized_end=529
  _globals['_CONVERSATIONMESSAGE']._serialized_start=531
  _globals['_CONVERSATIONMESSAGE']._serialized_end=610
  _globals['_DISPLAYCONVERSATIONRESPONSE']._serialized_start=612
  _globals['_DISPLAYCONVERSATIONRESPONSE']._serialized_end=714
  _globals['_SENDMESSAGEREQUEST']._serialized_start=716
  _globals['_SENDMESSAGEREQUEST']._serialized_end=835
  _globals['_SENDMESSAGERESPONSE']._serialized_start=837
  _globals['_SENDMESSAGERESPONSE']._serialized_end=858
  _globals['_READMESSAGESREQUEST']._serialized_start=860
  _globals['_READMESSAGESREQUEST']._serialized_end=953
  _globals['_READMESSAGESRESPONSE']._serialized_start=955
  _globals['_READMESSAGESRESPONSE']._serialized_end=977
  _globals['_DELETEMESSAGEREQUEST']._serialized_start=979
  _globals['_DELETEMESSAGEREQUEST']._serialized_end=1062
  _globals['_DELETEMESSAGERESPONSE']._serialized_start=1064
  _globals['_DELETEMESSAGERESPONSE']._serialized_end=1087
  _globals['_DELETEACCOUNTREQUEST']._serialized_start=1089
  _globals['_DELETEACCOUNTREQUEST']._serialized_end=1151
  _globals['_DELETEACCOUNTRESPONSE']._serialized_start=1153
  _globals['_DELETEACCOUNTRESPONSE']._serialized_end=1176
  _globals['_GETUNREADMESSAGESREQUEST']._serialized_start=1178
  _globals['_GETUNREADMESSAGESREQUEST']._serialized_end=1244
  _globals['_UNREADMESSAGEINFO']._serialized_start=1246
  _globals['_UNREADMESSAGEINFO']._serialized_end=1326
  _globals['_GETUNREADMESSAGESRESPONSE']._serialized_start=1328
  _globals['_GETUNREADMESSAGESRESPONSE']._serialized_end=1418
  _globals['_GETMESSAGEINFORMATIONREQUEST']._serialized_start=1420
  _globals['_GETMESSAGEINFORMATIONREQUEST']._serialized_end=1511
  _globals['_GETMESSAGEINFORMATIONRESPONSE']._serialized_start=1513
  _globals['_GETMESSAGEINFORMATIONRESPONSE']._serialized_end=1631
  _globals['_GETUSERNAMEBYIDREQUEST']._serialized_start=1633
  _globals['_GETUSERNAMEBYIDREQUEST']._serialized_end=1674
  _globals['_GETUSERNAMEBYIDRESPONSE']._serialized_start=1676
  _globals['_GETUSERNAMEBYIDRESPONSE']._serialized_end=1719
  _globals['_MARKMESSAGEASREADREQUEST']._serialized_start=1721
  _globals['_MARKMESSAGEASREADREQUEST']._serialized_end=1808
  _globals['_MARKMESSAGEASREADRESPONSE']._serialized_start=1810
  _globals['_MARKMESSAGEASREADRESPONSE']._serialized_end=1837
  _globals['_GETUSERBYUSERNAMEREQUEST']._serialized_start=1839
  _globals['_GETUSERBYUSERNAMEREQUEST']._serialized_end=1883
  _globals['_GETUSERBYUSERNAMERESPONSE']._serialized_start=1885
  _globals['_GETUSERBYUSERNAMERESPONSE']._serialized_end=1969
  _globals['_REQUESTVOTEREQUEST']._serialized_start=1971
  _globals['_REQUESTVOTEREQUEST']._serialized_end=2074
  _globals['_REQUESTVOTERESPONSE']._serialized_start=2076
  _globals['_REQUESTVOTERESPONSE']._serialized_end=2133
  _globals['_LOGENTRY']._serialized_start=2135
  _globals['_LOGENTRY']._serialized_end=2176
  _globals['_APPENDENTRIESREQUEST']._serialized_start=2179
  _globals['_APPENDENTRIESREQUEST']._serialized_end=2342
  _globals['_APPENDENTRIESRESPONSE']._serialized_start=2344
  _globals['_APPENDENTRIESRESPONSE']._serialized_end=2398
  _globals['_LEADERPINGREQUEST']._serialized_start=2400
  _globals['_LEADERPINGREQUEST']._serialized_end=2419
  _globals['_LEADERPINGRESPONSE']._serialized_start=2421
  _globals['_LEADERPINGRESPONSE']._serialized_end=2441
  _globals['_MESSAGINGSERVICE']._serialized_start=2535
  _globals['_MESSAGINGSERVICE']._serialized_end=3768
  _globals['_RAFTSERVICE']._serialized_start=3771
  _globals['_RAFTSERVICE']._serialized_end=3946
# @@protoc_insertion_point(module_scope)
