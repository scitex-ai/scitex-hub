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
 *  2. Target uid must be >= 10000 (pilot pool; avoids uid-1000 collisions).
 *  3. project_root must be absolute, contain no "..", and sit under
 *     USERS_TREE (compiled in: -DUSERS_TREE="/opt/scitex/data/users").
 *  4. image must be an absolute path ending in ".sif" (no URL pulls).
 *  5. port must be 18100-18999 (loopback pilot range).
 *  6. Environment is scrubbed: only FIGRECIPE_CONTAINER_AUTH_KEY,
 *     FIGRECIPE_DATA_ROOT=/work, FIGRECIPE_CONTAINER_PORT, PATH=/usr/bin:/bin
 *     and TMPDIR pass through. argv carries NO secrets (ps-safe).
 *  7. setresuid(uid)+setresgid(gid of target)+exec apptainer with the
 *     least-privilege flags (single project bind + own tmp, containment).
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
#define PORT_LO 18100
#define PORT_HI 18999

static int starts_with(const char *s, const char *prefix) {
    return strncmp(s, prefix, strlen(prefix)) == 0;
}

static int has_dotdot(const char *s) {
    return strstr(s, "..") != NULL;
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
    if (errno || !end || *end || uid < MIN_UID || uid > 60000) {
        fprintf(stderr, "spawn: uid refused\n");
        return 1;
    }
    /* 3. project_root gate */
    const char *root = argv[3];
    if (root[0] != '/' || has_dotdot(root) || !starts_with(root, USERS_TREE)) {
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
    long port = strtol(argv[5], &end, 10);
    if (errno || !end || *end || port < PORT_LO || port > PORT_HI) {
        fprintf(stderr, "spawn: port refused\n");
        return 1;
    }
    struct passwd *pw = getpwuid((uid_t)uid);
    if (!pw) {
        fprintf(stderr, "spawn: unknown uid\n");
        return 1;
    }
    /* 6. scrubbed environment */
    const char *auth = getenv("FIGRECIPE_CONTAINER_AUTH_KEY");
    if (!auth || !*auth) {
        fprintf(stderr, "spawn: auth key missing\n");
        return 1;
    }
    char portbuf[16], workdir[] = "/work";
    snprintf(portbuf, sizeof portbuf, "%ld", port);
    char tmpbind[4096], projbind[8192], tmpdir[4096];
    snprintf(tmpdir, sizeof tmpdir, "/tmp/figrecipe-%s", argv[4]);
    snprintf(tmpbind, sizeof tmpbind, "%s:/tmp/figrecipe:rw", tmpdir);
    snprintf(projbind, sizeof projbind, "%s:/work:rw", root);
    /* mkdir the per-user tmp as the TARGET user would see it is skipped:
     * the hub pre-creates /tmp/figrecipe-<user> owned by uid (Infra). */
    char *envp[] = {
        (char *)"PATH=/usr/bin:/bin",
        (char *)"PYTHONUNBUFFERED=1",
        (char *)"FIGRECIPE_DATA_ROOT=/work",
        NULL, NULL, NULL, NULL
    };
    char authbuf[4096], portenv[64], tmpenv[4096];
    snprintf(authbuf, sizeof authbuf, "FIGRECIPE_CONTAINER_AUTH_KEY=%s", auth);
    snprintf(portenv, sizeof portenv, "FIGRECIPE_CONTAINER_PORT=%s", portbuf);
    snprintf(tmpenv, sizeof tmpenv, "TMPDIR=/tmp/figrecipe");
    envp[3] = authbuf; envp[4] = portenv; envp[5] = tmpenv;
    (void)workdir;
    /* 7. uid switch + exec (least-privilege apptainer flags) */
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
