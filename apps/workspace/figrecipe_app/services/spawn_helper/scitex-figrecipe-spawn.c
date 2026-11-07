/* scitex-figrecipe-spawn — minimal privileged spawner (AUDITED pilot surface).
 *
 * Purpose: switch to the requesting user's uid, then exec apptainer. Installed
 * setuid-root at /usr/local/sbin/scitex-figrecipe-spawn, owned root:scitex-hub,
 * mode 4750 (only the hub service account can execute it).
 *
 * Usage: scitex-figrecipe-spawn <uid> <image> <project_root> <username> <port>
 *
 * Policy (fail closed, no config files — everything is argv + allowlist):
 *  1. Caller euid/egid must be the hub service account (HUB_UID, compiled in
 *     by Infra at install: -DHUB_UID=$(id -u scitex-hub)).
 *  2. Target uid must be >= MIN_UID (10000, pilot pool; avoids uid-1000
 *     collisions) and <= MAX_UID (60000, mirrors the hub layer ceiling).
 *  3. project_root must be absolute, contain no "..", and sit under
 *     USERS_TREE (compiled in: -DUSERS_TREE="/opt/scitex/data/users") with
 *     a path boundary (exact tree or tree + '/'), so users-evil is refused.
 *  4. image must be an absolute path ending in ".sif" (no URL pulls).
 *  5. port must be 18100-18999 (loopback pilot range).
 *  6. username (argv[4]) must match [A-Za-z0-9_.-]+ (max 128 chars): it is
 *     interpolated into the per-user tmp bind source, and a setuid-root
 *     context must never let '/' or ".." smuggle a foreign host path in.
 *  7. Environment is scrubbed: only FIGRECIPE_CONTAINER_AUTH_KEY,
 *     FIGRECIPE_DATA_ROOT=/work, FIGRECIPE_CONTAINER_PORT, PATH=/usr/bin:/bin
 *     and TMPDIR pass through. argv carries NO secrets (ps-safe).
 *  8. Supplementary groups are cleared with setgroups(0, NULL) BEFORE
 *     setresgid/setresuid, while still euid-root — otherwise the hub's
 *     group memberships leak into the target-uid process. Then
 *     setresuid(uid)+setresgid(gid of target)+exec apptainer with the
 *     least-privilege flags (single project bind + own tmp, containment).
 *  9. Every snprintf is truncation-checked: a truncated bind string would
 *     silently redirect a mount, so truncation fails closed.
 *
 * Build: cc -O2 -Wall -Wextra -DHUB_UID=1001 -DUSERS_TREE='"/opt/scitex/data/users"' \
 *          -o scitex-figrecipe-spawn scitex-figrecipe-spawn.c
 * Install: install -o root -g scitex-hub -m 4750 scitex-figrecipe-spawn \
 *          /usr/local/sbin/scitex-figrecipe-spawn
 *
 * Infra owns steps above; this source is the audit record (reviewed in the
 * pilot PR, never modified on-host).
 */
#define _GNU_SOURCE
#include <errno.h>
#include <grp.h>
#include <pwd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>

#ifndef HUB_UID
#define HUB_UID 1001
#endif
#ifndef USERS_TREE
#define USERS_TREE "/opt/scitex/data/users"
#endif
#define MIN_UID 10000
#define MAX_UID 60000
#define PORT_LO 18100
#define PORT_HI 18999
#define MAX_USERNAME_LEN 128

static int has_dotdot(const char *s) {
    return strstr(s, "..") != NULL;
}

/* Strict allowlist for login names used in the tmp-bind path. Fail closed:
 * empty, over-long, or any byte outside [A-Za-z0-9_.-] is refused ('/' and
 * ".." can never survive this set, but has_dotdot + '/' are also checked
 * at the call site for defense in depth). */
static int valid_username(const char *s) {
    size_t i, n;
    if (!s)
        return 0;
    n = strlen(s);
    if (n == 0 || n > MAX_USERNAME_LEN)
        return 0;
    for (i = 0; i < n; i++) {
        char c = s[i];
        int ok = (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
                 (c >= '0' && c <= '9') || c == '_' || c == '.' || c == '-';
        if (!ok)
            return 0;
    }
    return 1;
}

/* Tree confinement with a path boundary: exact-tree or tree-then-'/'.
 * A bare prefix match would accept USERS_TREE + "-evil". */
static int under_tree(const char *path, const char *tree) {
    size_t len;
    if (!path || !tree)
        return 0;
    len = strlen(tree);
    if (strncmp(path, tree, len) != 0)
        return 0;
    return path[len] == '\0' || path[len] == '/';
}

/* snprintf with truncation treated as failure (a shortened bind string
 * would silently redirect a mount — fail closed instead). Returns 0 ok. */
static int checked_snprintf(char *buf, size_t size, const char *fmt, const char *a, const char *b) {
    int n = snprintf(buf, size, fmt, a, b);
    if (n < 0 || (size_t)n >= size)
        return -1;
    return 0;
}

int main(int argc, char **argv) {
    if (argc != 6) {
        fprintf(stderr, "usage: %s <uid> <image> <project_root> <username> <port>\n", argv[0]);
        return 2;
    }
    /* 1. caller gate */
    if ((int)getuid() != HUB_UID && (int)geteuid() != HUB_UID) {
        fprintf(stderr, "spawn: caller not authorized\n");
        return 1;
    }
    /* 2. uid gate */
    char *end = NULL;
    errno = 0;
    long uid = strtol(argv[1], &end, 10);
    if (errno || !end || *end || uid < MIN_UID || uid > MAX_UID) {
        fprintf(stderr, "spawn: uid refused\n");
        return 1;
    }
    /* 3. project_root gate */
    const char *root = argv[3];
    if (root[0] != '/' || has_dotdot(root) || !under_tree(root, USERS_TREE)) {
        fprintf(stderr, "spawn: project bind refused\n");
        return 1;
    }
    /* 4. image gate */
    const char *image = argv[2];
    size_t ilen = strlen(image);
    if (image[0] != '/' || ilen < 5 || strcmp(image + ilen - 4, ".sif") != 0 || has_dotdot(image)) {
        fprintf(stderr, "spawn: image refused\n");
        return 1;
    }
    /* 5. port gate */
    errno = 0;
    long port = strtol(argv[5], &end, 10);
    if (errno || !end || *end || port < PORT_LO || port > PORT_HI) {
        fprintf(stderr, "spawn: port refused\n");
        return 1;
    }
    /* 6. username gate (setuid tmp-bind path: allowlist only) */
    const char *username = argv[4];
    if (!valid_username(username) || strchr(username, '/') != NULL || has_dotdot(username)) {
        fprintf(stderr, "spawn: username refused\n");
        return 1;
    }
    struct passwd *pw = getpwuid((uid_t)uid);
    if (!pw) {
        fprintf(stderr, "spawn: unknown uid\n");
        return 1;
    }
    /* 7. scrubbed environment */
    const char *auth = getenv("FIGRECIPE_CONTAINER_AUTH_KEY");
    if (!auth || !*auth) {
        fprintf(stderr, "spawn: auth key missing\n");
        return 1;
    }
    char portbuf[16], workdir[] = "/work";
    {
        int n = snprintf(portbuf, sizeof portbuf, "%ld", port);
        if (n < 0 || (size_t)n >= sizeof portbuf) {
            fprintf(stderr, "spawn: port format refused\n");
            return 1;
        }
    }
    char tmpbind[4096], projbind[8192], tmpdir[4096];
    if (checked_snprintf(tmpdir, sizeof tmpdir, "/tmp/figrecipe-%s", username, "") != 0) {
        fprintf(stderr, "spawn: tmp path refused\n");
        return 1;
    }
    if (checked_snprintf(tmpbind, sizeof tmpbind, "%s:/tmp/figrecipe:rw", tmpdir, "") != 0) {
        fprintf(stderr, "spawn: tmp bind refused\n");
        return 1;
    }
    if (checked_snprintf(projbind, sizeof projbind, "%s:/work:rw", root, "") != 0) {
        fprintf(stderr, "spawn: project bind refused\n");
        return 1;
    }
    /* mkdir the per-user tmp as the TARGET user would see it is skipped:
     * the hub pre-creates /tmp/figrecipe-<user> owned by uid (Infra). */
    char *envp[] = {
        (char *)"PATH=/usr/bin:/bin",
        (char *)"PYTHONUNBUFFERED=1",
        (char *)"FIGRECIPE_DATA_ROOT=/work",
        NULL, NULL, NULL, NULL
    };
    char authbuf[4096], portenv[64], tmpenv[4096];
    if (checked_snprintf(authbuf, sizeof authbuf, "FIGRECIPE_CONTAINER_AUTH_KEY=%s", auth, "") != 0 ||
        checked_snprintf(portenv, sizeof portenv, "FIGRECIPE_CONTAINER_PORT=%s", portbuf, "") != 0 ||
        checked_snprintf(tmpenv, sizeof tmpenv, "%s", "TMPDIR=/tmp/figrecipe", "") != 0) {
        fprintf(stderr, "spawn: environment refused\n");
        return 1;
    }
    envp[3] = authbuf; envp[4] = portenv; envp[5] = tmpenv;
    (void)workdir;
    /* 8. drop supplementary groups FIRST (still euid-root: only root may
     * call setgroups), then uid switch + exec (least-privilege flags) */
    if (setgroups(0, NULL) != 0) {
        fprintf(stderr, "spawn: setgroups failed\n");
        return 1;
    }
    if (setresgid(pw->pw_gid, pw->pw_gid, pw->pw_gid) != 0) {
        fprintf(stderr, "spawn: setresgid failed\n");
        return 1;
    }
    if (setresuid((uid_t)uid, (uid_t)uid, (uid_t)uid) != 0) {
        fprintf(stderr, "spawn: setresuid failed\n");
        return 1;
    }
    char *args[] = {
        (char *)"apptainer", (char *)"run",
        (char *)"--contain", (char *)"--cleanenv", (char *)"--no-home",
        (char *)"--pid", (char *)"--ipc",
        (char *)"-B", projbind,
        (char *)"-B", tmpbind,
        (char *)image,
        NULL
    };
    /* NOTE: the secret travels in the scrubbed execve ENVIRONMENT (envp
     * above), never in argv — `ps` output carries no credentials. */
    execve("/usr/bin/apptainer", args, envp);
    fprintf(stderr, "spawn: exec failed: %s\n", strerror(errno));
    return 1;
}
