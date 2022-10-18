class NotSendInTelegram(Exception):
	pass


class CannotSendMessageToTelegram(NotSendInTelegram):
	pass


class CannotSendRequestToServer(Exception):
	pass


class EndpointNotAvailable(Exception):
	pass


class IsNotDict(TypeError):
	pass


class ServerNotSentKey(KeyError):
	pass


class ServerNotSentListHomeworks(TypeError):
	pass


class NotDocumentedStatusHomework(KeyError):
	pass
