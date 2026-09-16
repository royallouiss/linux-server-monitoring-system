 .. _users:

Users
======================================================================

Starting a new project, it’s highly recommended to set up a custom user model, 
even if the default User model is sufficient for you. 

This model behaves identically to the default user model, 
but you’ll be able to customize it in the future if the need arises.

Roles & Access Control
----------------------------------------------------------------------

The system implements Role-Based Access Control (RBAC) with three primary roles:

- **Admin**: Full control (add/edit/delete servers, configure alerts, manage users).
- **Operator**: Operational management (add/edit servers, view monitoring & alerts).
- **Viewer**: Read-only observation (view dashboard, view metrics, view alerts).

.. automodule:: linux_server_monitoring_system.users.models
   :members:
   :noindex:


