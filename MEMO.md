<!-- ---
!-- Timestamp: 2025-12-07 08:13:28
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/MEMO.md
!-- --- -->

I lost data in the last 5 hours.

For example,

In the /scholar/#search page, the placeholder of the textarea should have
syntax like

hippocampus -t human -t -mouse ...
This means title includes human but not mouse

This must have written in the tooltip contents as well

Also, the panel resizer and expand/shrink did synchronized, as well as the global header expand/shrink to upwards with downwards arrow from the center bottom

In the landing page, snake icon was introduced, and

"""
SciTeX Ecosystem
Integrated research tools from literature to publication
"""

was revised as 

"""
SciTeX Ecosystem
From data to publication - all in one.
"""

✅ 1. git reflog を見てください（最も重要）

Git が追跡しているすべての過去の HEAD の移動ログです。

git reflog


ここに、あなたが作業していたブランチの過去2時間のコミットやステージ状態が残っている可能性があります。

見つかったら、そのコミットに戻す：

git checkout <commit-hash>


またはブランチをそこに戻す：

git reset --hard <commit-hash>

✅ 2. ステージされていたファイルは復活できる可能性があります

もし git add はしていたが commit していなかった場合：

git fsck --lost-found


ここに残っている “dangling blob（浮遊オブジェクト）” を確認できます。

✅ 3. git stash に自動退避されていないか

たまに、pull/merge でコンフリクトが起きた時に自動的に stash に逃がされるケースがあります。

git stash list
git stash show -p stash@{0}

✅ 4. IDE の autosave / local history

もし VS Code / PyCharm / Emacs を使っているなら:

VS Code
. config/Code/Backups/


に過去の自動バックアップがあります。

Emacs

auto-save-list や #filename# に一時保存されます。

✅ 5. Django / Docker / SciTeX バックエンドのログ

もし web UI から生成した要素なら、
Docker コンテナの volumes に JSON が残っている可能性があります。

<!-- EOF -->