class ToSendInTelegram(Exception):
	pass


class CannotSendMessageToTelegram(Exception):
	pass


class CannotSendRequestToServer(Exception):
	pass


class EndpointNotAvailable(ToSendInTelegram):
	pass


class ResponseIsNotDictOrList(TypeError):
	pass


class HomeworkIsNotDictOrList(TypeError):
	pass


class ServerNotSentKeyDate(KeyError):
	pass


class ServerNotSentKeyHomeworks(KeyError):
	pass


class ServerNotSentListHomeworks(TypeError):
	pass


class NotDocumentedStatusHomework(KeyError, ToSendInTelegram):
	pass


class ServerSentEmptyListHomeworks(Exception):
	pass


class SameMessageNotSending(Exception):
	pass
