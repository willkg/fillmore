from fillmore.scrubber import Scrubber, Rule, build_scrub_cookies

# Create a Scrubber
scrubber = Scrubber(
    rules=[
        Rule(
            path="request",
            keys=["cookies"],
            # build_scrub_cookies builds a scrub function that handles the
            # different possible shapes of the value, scrubs the specified
            # bits, and returns the same shape
            scrub=build_scrub_cookies(params=["code", "state"]),
        ),
        Rule(
            path="request.headers",
            keys=["Auth-Token", "X-Forwarded-For"],
            # You can specify scrub functions as functions or Python dotted
            # paths
            scrub="scrub",
        ),
        Rule(
            path="exception.values.[].stacktrace.frames.[].vars",
            keys=["username"],
            scrub="scrub",
        ),
    ],
)
