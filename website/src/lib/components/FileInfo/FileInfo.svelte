<script lang="ts">
	export let filename: string;
</script>

<li class="w-full card p-4">
	<a href="/api/file/{filename}">
		<div class="">
			{filename}
		</div>
	</a>
</li>
