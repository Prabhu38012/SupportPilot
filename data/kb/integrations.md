# Integrations and API

## Connect Slack
Open Settings > Integrations > Slack and click Connect. Choose the workspace and channel to link. Once linked, new task comments and status changes post to the channel, and you can create tasks with the /acme command.

## GitHub integration
Connect GitHub under Settings > Integrations > GitHub. Mention a task ID such as ACME-123 in a pull request title or commit message to link it to the task. Linked tasks move to Done automatically when the pull request is merged.

## Importing from Jira
Jira is supported as a one-time CSV import under Settings > Import. Two-way Jira sync is not available.

## Google Calendar
Task due dates can be shown in Google Calendar through a read-only calendar feed. Editing tasks from the calendar is not supported.

## API access and rate limits
Create personal API tokens under Settings > Developer. The REST API allows 100 requests per minute per token. Requests above the limit receive HTTP 429 and should be retried after the time in the Retry-After header.

## Webhooks
Webhooks can be configured under Settings > Developer > Webhooks for task created, updated and completed events. Failed deliveries are retried 5 times with exponential backoff.
