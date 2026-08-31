package io.github.txllthemall.skeuoos;

import android.app.Activity;
import android.os.Bundle;
import android.provider.Settings;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {
    private TextView text(String s, int sp, boolean bold) {
        TextView t = new TextView(this);
        t.setText(s); t.setTextSize(sp); t.setTextColor(Color.WHITE);
        t.setPadding(0, 12, 0, 12);
        if (bold) t.setTypeface(Typeface.DEFAULT_BOLD);
        return t;
    }
    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(48, 48, 48, 48);
        root.setBackgroundColor(Color.rgb(20,21,24));
        root.addView(text("SkeuoOS", 34, true));
        root.addView(text("Skeuomorphic icon pack tuned for the stock OnePlus / OxygenOS launcher.", 17, false));
        root.addView(text("Apply: Settings → Wallpapers & style → Icons → SkeuoOS. Apply the pack once and mapped apps will use SkeuoOS automatically.", 16, false));
        root.addView(text("This build ships its own artwork and does not require Nova, Lawnchair, or any background service.", 15, false));
        Button home = new Button(this); home.setText("Open Home settings");
        home.setOnClickListener(v -> {
            try { startActivity(new Intent(Settings.ACTION_HOME_SETTINGS)); }
            catch (Exception e) { Toast.makeText(this, "Open Wallpapers & style → Icons manually", Toast.LENGTH_LONG).show(); }
        });
        root.addView(home);
        Button details = new Button(this); details.setText("App info");
        details.setOnClickListener(v -> startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:" + getPackageName()))));
        root.addView(details);
        TextView foot=text("66 icons • 152 component mappings • no ads • no tracking",14,false); foot.setGravity(Gravity.CENTER_HORIZONTAL); root.addView(foot);
        setContentView(root);
    }
}
