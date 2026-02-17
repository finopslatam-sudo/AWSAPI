class BaseAudit:
    """
    Clase base para todas las auditorías.
    Obliga a implementar el método run().
    """

    def __init__(self, boto_session, client_id, aws_account):
        self.session = boto_session
        self.client_id = client_id
        self.aws_account = aws_account

    def run(self):
        raise NotImplementedError("Audit must implement run()")
